from index import GeospatialIndex
import redis
import time

class RedisIndex(GeospatialIndex):
    def __init__(self):
        super().__init__()
        REDIS_HOST = "localhost"
        REDIS_PORT = 6379

        self.REDIS_GEO_KEY = "aircraft_positions"
        self.REDIS_GEO_BACKUP_KEY = "aircraft_positions_backup"
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        self.metadata = {}
        self.r.flushall()

    def store_metadata(self, transaction, icao24, fields):
        transaction.hset(f"aircraft:{icao24}", mapping=fields)

    def run_transaction(self, transaction):
        transaction.execute()

    def remove_finished_aircrafts(self, transaction):
        for key in self.metadata:
            if key not in self.new_metadata:
                transaction.delete(key)

    def init_transaction(self):
        return self.r.pipeline(transaction=False)

    def store_in_index(self, transaction, icao24, aircraft, quasi_static_optimization, add_optimization):
        transaction.geoadd(
            self.REDIS_GEO_KEY,
            (aircraft['longitude'], aircraft['latitude'], icao24)
        )
        return 1

    '''def process_aicrafts(self, aircrafts_chunk, optimizer=False, quasi_static=True):
        pipeline = self.r.pipeline(transaction=False)
        stored_aircrafts = []
        for aircraft in aircrafts_chunk:
            icao24 = aircraft[0]
            callsign = aircraft[1]
            longitude = aircraft[5]
            latitude = aircraft[6]
            on_ground = aircraft[8]
            velocity = aircraft[9]
            if velocity is not None:
                velocity = self.convert_speed_to_knots(float(velocity))
            altitude = aircraft[13]
            if altitude is not None:
                altitude = self.convert_altitude_to_feet(float(altitude))

            # Ignore invalid coordinates
            if latitude is None or longitude is None:
                continue

            skip = False
            if quasi_static and on_ground:
                skip = True

            metadata_key = icao24
            if not skip or not self.is_stored_in_index(metadata_key):
                pipeline.geoadd(
                    self.REDIS_GEO_KEY,
                    (longitude, latitude, icao24)
                )
                stored_aircrafts.append(icao24)

            metadata_key = f"aircraft:{metadata_key}"
           # if metadata_key in self.metadata:
              #  self.metadata[metadata_key]['processed'] = True
            pipeline.hset(metadata_key, mapping={
                "callsign": callsign or "",
                "latitude": latitude,
                "longitude": longitude,
                "velocity": velocity or 0,
                "altitude": altitude or 0,
            })
            self.metadata[metadata_key] = {
                "callsign": callsign or "",
                "latitude": latitude,
                "longitude": longitude,
                "velocity": velocity or 0,
                "altitude": altitude or 0,
                "processed": True
            }




        keys = []
        for key in self.metadata:
            if self.metadata[key]['processed'] is not None and self.metadata[key]['processed'] is False:
                pipeline.delete(key)
                icao = key.split(":")[1]
                pipeline.zrem(self.REDIS_GEO_KEY,  icao)
                keys.append(key)
            else:
                self.metadata[key] = {

                }
        result = pipeline.execute()

        for key in keys:
            self.metadata.pop(key)

    geohash_pipeline = self.r.pipeline(transaction=False)
        for aircraft in stored_aircrafts:
            geohash_pipeline.geohash(self.REDIS_GEO_KEY, aircraft)
        geohashes = geohash_pipeline.execute()
        for aircraft, geohash in zip(geohashes, stored_aircrafts):
            pass'''



    def load_in_memory(self):
        pass
        '''self.metadata = {}
        keys = list(self.r.scan_iter("aircraft:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.hgetall(key)
        aircrafts = pipe.execute()

        if len(keys) > 0:
            for key, aircraft in zip(keys, aircrafts):
                self.metadata[key] = aircraft
                self.metadata[key]['processed'] = False'''

    def create_backup(self):
        t0 = time.perf_counter()
        self.r.copy(self.REDIS_GEO_KEY, self.REDIS_GEO_BACKUP_KEY)
        t1 = time.perf_counter()
        print(f"Backup time: {t1 - t0:.4f} seconds")


    def nearby_aircraft_monitor(self, update_in_progress):
        try:
            index = self.REDIS_GEO_KEY
            if update_in_progress:
                index = self.REDIS_GEO_BACKUP_KEY
            nearby = self.r.geosearch(
                index,
                longitude=28.72,
                latitude=41.27,
                radius=100,
                unit="km"
            )

            '''print(
                f"Aircraft near Cluj: {len(nearby)}, update is: {update_in_progress}"
            )'''
            for icao24 in nearby:
                details = self.r.hgetall(f"aircraft:{icao24}")
                print(icao24, details)

        except Exception as e:
            print("Query error:", e)

    def get_memory_usage(self):
        index_size = self.r.memory_usage(self.REDIS_GEO_KEY)
        metadata_size = 0
        for key in self.r.scan_iter("aircraft:*"):
            metadata_size += self.r.memory_usage(key)

        megabyte_size = 1024 * 1024
        index_size /= megabyte_size
        metadata_size /= megabyte_size

        print(f"Index size: {index_size} MB, Metadata size: {metadata_size} MB")
        return index_size, metadata_size

