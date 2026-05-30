from collections import defaultdict
from threading import Lock
import redis
import h3

from index import GeospatialIndex


class UberIndex(GeospatialIndex):
    def __init__(self):
        super().__init__()
        self.cell_to_aircraft = defaultdict(set)
        self.aircraft_metadata = {}
        self.resolution = 2
        REDIS_HOST = "localhost"
        REDIS_PORT = 6379
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        self.r.flushall()
        self.old_cells = {}
        self.iteration = 0

    def load_in_memory(self):
        '''keys = list(self.r.scan_iter("cell:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.lrange(key, 0, -1)
        cells_results = pipe.execute()

        for key, result in zip(keys, cells_results):
            cell = key.split(":")[1]
            self.cell_to_aircraft[cell] = result'''


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

    def nearby_aircraft_monitor(self, update_in_progress):
        lng = 28.72
        lat = 41.27
        center_cell = h3.latlng_to_cell(
            lat,
            lng,
            self.resolution
        )
        k = 0
        nearby_cells = h3.grid_disk(center_cell, k)
        candidates = set()
        for cell in nearby_cells:
            aircrafts = self.r.lrange(f"cell:{cell}", 0, -1)
            candidates.update(aircrafts)

        results = []

        pipe = self.r.pipeline()
        for icao24 in candidates:
            pipe.hgetall(f"aircraft:{icao24}")
        candidates = pipe.execute()


        for candidate in candidates:
            if candidate["latitude"] is None or candidate["longitude"] is None:
                continue
            distance = h3.great_circle_distance(
                (lat, lng),
                (float(candidate["latitude"]), float(candidate["longitude"])),
                unit="km"
            )
            if distance <= 100:
                results.append(candidate)
        return results