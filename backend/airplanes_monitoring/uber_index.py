from collections import defaultdict
import redis
import h3

from .index import GeospatialIndex


class UberIndex(GeospatialIndex):
    def __init__(self):
        super().__init__()
        self.cell_to_aircraft = defaultdict(set)
        self.aircraft_metadata = {}
        self.resolution = 3
        REDIS_HOST = "localhost"
        REDIS_PORT = 6379
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        #self.r.flushall()
        self.old_cells = {}
        self.iteration = 0
        self.load_in_memory()

    def load_in_memory(self):
        '''keys = list(self.r.scan_iter("cell:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.lrange(key, 0, -1)
        cells_results = pipe.execute()

        for key, result in zip(keys, cells_results):
            cell = key.split(":")[1]
            self.cell_to_aircraft[cell] = result'''

        self.metadata = {}
        keys = list(self.r.scan_iter("backup:aircraft:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.hgetall(key)
        aircrafts = pipe.execute()
        '''count = 100
        for aircraft in aircrafts:
            count -= 1
            print(aircraft)
            if count == 0:
                break'''
        print('loaded: ', len(aircrafts))
        if len(keys) > 0:
            for key, aircraft in zip(keys, aircrafts):
                self.metadata[key] = aircraft
                self.metadata[key]['processed'] = False

    def create_backup(self):
        pipe = self.r.pipeline(transaction=False)
        for key in self.r.scan_iter("aircraft:*"):
            backup_key = key.replace("aircraft:", "backup:aircraft:")
            pipe.copy(key, backup_key, replace=True)
        pipe.execute()

    def store_metadata(self, transaction, icao24, fields):
        transaction.hset(f"aircraft:{icao24}", mapping=fields)

    def get_cell(self, aircraft):
        return h3.latlng_to_cell(aircraft['latitude'], aircraft['longitude'], self.resolution)

    def store_in_index(self, transaction, icao24, aircraft, quasi_static_optimization, add_optimization):
        if icao24 in self.metadata and aircraft['on_ground'] and quasi_static_optimization:
            return 0
        if add_optimization and icao24 in self.metadata and self.metadata[icao24]['cell'] == aircraft['cell']:
            return 0

        count = 0
        if icao24 in self.metadata:
            transaction.lrem(f"cell:{self.metadata[icao24]['cell']}", 1, icao24)
            count += 1
        transaction.rpush(f"cell:{aircraft['cell']}", icao24)
        ''' 
                TEST HOW CELL LISTS LOOK LIKE BEFORE AND AFTER + HANDLE ALSO self.cell_to_aircraft
        '''

        count += 1
        return count

    def run_transaction(self, transaction):
        transaction.execute()

    def remove_finished_aircrafts(self, transaction):
        for key in self.metadata:
            if key not in self.new_metadata:
                transaction.delete(key)

    def init_transaction(self):
        return self.r.pipeline(transaction=False)

    def nearby_aircraft_monitor(self, lng, lat, update_in_progress):
        center_cell = h3.latlng_to_cell(
            lat,
            lng,
            self.resolution
        )
        k = 1
        nearby_cells = h3.grid_disk(center_cell, k)
        candidates = set()
        for cell in nearby_cells:
            aircrafts = self.r.lrange(f"cell:{cell}", 0, -1)
            candidates.update(aircrafts)

        results = []

        pipe = self.r.pipeline()
        for icao24 in candidates:
            key = f"aircraft:{icao24}"
            if update_in_progress:
                key = f"backup:aircraft:{icao24}"
            pipe.hgetall(key)
        candidates = pipe.execute()
        print('update in query: ', update_in_progress)
        for candidate in candidates:
            try:
                if len(candidate) == 0 or candidate["latitude"] is None or candidate["longitude"] is None:
                    continue
                candidate["latitude"] = float(candidate["latitude"])
                candidate["longitude"] = float(candidate["longitude"])

                distance = h3.great_circle_distance(
                    (lat, lng),
                    (float(candidate["latitude"]), float(candidate["longitude"])),
                    unit="km"
                )
                if distance <= 100:
                    results.append(candidate)
            except ValueError:
                print('failed: ', candidate)
        return results


    def get_memory_usage(self):
        index_size = 0
        metadata_size = 0
        for key in self.r.scan_iter("aircraft:*"):
            metadata_size += self.r.memory_usage(key)
        for key in self.r.scan_iter("cell:*"):
            index_size += self.r.memory_usage(key)

        megabyte_size = 1024 * 1024
        index_size /= megabyte_size
        metadata_size /= megabyte_size

        print(f"Index size: {index_size} MB, Metadata size: {metadata_size} MB")
        return index_size, metadata_size