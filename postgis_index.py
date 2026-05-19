import psycopg2
import time

from index import GeospatialIndex


class PostGISIndex(GeospatialIndex):

    def __init__(self):
        super().__init__()
        self.conn = psycopg2.connect(
            dbname="aircraft_db",
            user="postgres",
            password="password",
            host="localhost",
            port=5432
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

        # Create table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_positions (
            icao24 TEXT,
            location GEOGRAPHY(POINT, 4326)
        );
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_metadata (
            icao24 TEXT PRIMARY KEY,
            callsign TEXT,
            velocity DOUBLE PRECISION,
            altitude DOUBLE PRECISION,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION
        );
        """)

        self.cursor.execute("DELETE FROM aircraft_positions;")
        self.cursor.execute("DELETE FROM aircraft_metadata;")
        self.cursor.execute("DELETE FROM aircraft_positions_backup;")

        # Create spatial index
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_icao
            ON aircraft_metadata(icao24);
        """)

        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_aircraft_location
        ON aircraft_positions
        USING GIST (location);
        """)

        # Backup table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS aircraft_positions_backup
        (LIKE aircraft_positions INCLUDING ALL);
        """)

    def store_in_index(self, icao24, latitude, longitude):
        #cursor = self.conn.cursor()
        self.cursor.execute("""
        INSERT INTO aircraft_positions (
            icao24,
            location
        )
        VALUES (
            %s,
            ST_SetSRID(
                ST_MakePoint(%s, %s),
                4326
            )::GEOGRAPHY
        )

        ON CONFLICT (icao24)
        DO UPDATE SET
            location = EXCLUDED.location;
        """, (
            icao24,
            longitude,
            latitude
        ))

    def store_metadata(self, metadata_key, callsign, latitude, longitude, velocity, altitude):
        #cursor = self.conn.cursor()
        self.cursor.execute("""
        INSERT INTO aircraft_metadata (
            icao24,
            callsign,
            latitude,
            longitude,
            velocity,
            altitude)

        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (icao24)
        DO UPDATE SET
            callsign = EXCLUDED.callsign,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            velocity = EXCLUDED.velocity,
            altitude = EXCLUDED.altitude
        """, (
            metadata_key,
            callsign or "",
            latitude,
            longitude,
            velocity or 0,
            altitude or 0,
        ))

    def is_stored_in_index(self, icao24):
        #cursor = self.conn.cursor()
        self.cursor.execute("""
        SELECT 1 FROM aircraft_metadata
        WHERE icao24 = %s
        LIMIT 1;
        """, (icao24,))
        return self.cursor.fetchone() is not None


    def create_backup(self):
        t0 = time.perf_counter()

        self.cursor.execute("DELETE FROM aircraft_positions_backup;")

        self.cursor.execute("""
        INSERT INTO aircraft_positions_backup
        SELECT * FROM aircraft_positions;
        """)

        t1 = time.perf_counter()

        print(f"Backup time: {t1 - t0:.4f} seconds")


    def nearby_aircraft_monitor(self, update_in_progress):
        try:
            positions_table = "aircraft_positions"
            metadata_table = "aircraft_metadata"
            if update_in_progress:
                positions_table = "aircraft_positions_backup"
                metadata_table = "aircraft_metadata_backup"

            cursor = self.conn.cursor()
            cursor.execute(f"""
            SELECT
                m.icao24,
                m.callsign,
                m.latitude,
                m.longitude,
                m.velocity,
                m.altitude

            FROM {positions_table} p

            JOIN {metadata_table} m
                ON p.icao24 = m.icao24

            WHERE ST_DWithin(
                p.location,
                ST_SetSRID(
                    ST_MakePoint(%s, %s),
                    4326
                )::GEOGRAPHY,
                %s
            );
            """, (23.59, 46.77, 100000))

            nearby_aircraft = cursor.fetchall()

            '''print(
                f"Aircraft near Cluj: "
                f"{len(nearby_aircraft)}, "
                f"update is: {update_in_progress}"
            )'''

            results = []
            for aircraft in nearby_aircraft:
                results.append({
                    "icao24": aircraft[0],
                    "callsign": aircraft[1],
                    "latitude": aircraft[2],
                    "longitude": aircraft[3],
                    "velocity": aircraft[4],
                    "altitude": aircraft[5]
                })
            return results

        except Exception as e:
            print("Query error:", e)


    def get_memory_usage(self):
        self.cursor.execute("""
        SELECT
            pg_size_pretty(pg_total_relation_size('aircraft_positions')) AS positions_size,
            pg_size_pretty(pg_total_relation_size('aircraft_metadata')) AS metadata_size;
        """)

        results = self.cursor.fetchall()
        index_size, metadata_size = results[0]
        value, unit = index_size.split()
        index_size_mb = float(value) / 1024
        value, unit = metadata_size.split()
        metadata_size_mb = float(value) / 1024
        return index_size_mb, metadata_size_mb