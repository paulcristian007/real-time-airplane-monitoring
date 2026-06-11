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

    def load_in_memory(self):
        pass

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

            pipe = self.r.pipeline()
            for icao24 in nearby:
                pipe.hgetall(f"aircraft:{icao24}")
                #print(icao24, details)
            results = pipe.execute()
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

