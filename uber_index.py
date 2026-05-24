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
        self.resolution = 3
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
        self.metadata = {}
        keys = list(self.r.scan_iter("aircraft:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.hgetall(key)

        aircrafts = pipe.execute()
        if len(keys) > 0:
            for key, aircraft in zip(keys, aircrafts):
                self.metadata[key] = aircraft
                self.metadata[key]['processed'] = False

        keys = list(self.r.scan_iter("cell:*"))
        pipe = self.r.pipeline(transaction=False)
        for key in keys:
            pipe.lrange(key, 0, -1)
        cells_results = pipe.execute()

        for key, result in zip(keys, cells_results):
            cell = key.split(":")[1]
            self.cell_to_aircraft[cell] = result


    def cell_did_not_change(self, icao24, cell, optimizer, skip):
        if skip:
            return True
        if not optimizer:
            return False
        return icao24 in self.old_cells and cell == self.old_cells[icao24]

    def process_aicrafts(self, aircrafts_chunk, optimizer=True, quasi_static=True):
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

            cell = h3.latlng_to_cell(latitude, longitude, self.resolution)
            if self.cell_did_not_change(icao24, cell, optimizer, skip):
                skip = True
            elif icao24 in self.old_cells:
                pipeline.lrem(f"cell:{self.old_cells[icao24]}", 1, icao24)
            '''if not skip:
                if optimizer and icao24 in self.old_cells and self.old_cells[icao24] == cell:
                    skip = True
                    equalizer += 1
                elif not optimizer and icao24 in self.old_cells:
                    pipeline.lrem(f"cell:{self.old_cells[icao24]}", 1, icao24)
                    count += 1'''
            self.old_cells[icao24] = cell

            metadata_key = f"aircraft:{icao24}"
            if not skip or not self.is_stored_in_index(metadata_key):
                pipeline.rpush(f"cell:{cell}", icao24)
                stored_aircrafts.append(icao24)

            if metadata_key in self.metadata:
                self.metadata[metadata_key]['processed'] = True

            if not on_ground or not self.is_stored_in_index(metadata_key):
                pipeline.hset(metadata_key, mapping={
                    "callsign": callsign or "",
                    "latitude": latitude,
                    "longitude": longitude,
                    "velocity": velocity or 0,
                    "altitude": altitude or 0,
                })

        for key in self.metadata:
            if self.metadata[key]['processed'] is not None and self.metadata[key]['processed'] is False:
                pipeline.delete(key)

        result = pipeline.execute()


    def nearby_aircraft_monitor(self, update_in_progress):
        lng = 28.72
        lat = 41.27
        center_cell = h3.latlng_to_cell(
            lat,
            lng,
            self.resolution
        )
        k = 1
        nearby_cells = h3.grid_disk(center_cell, k)
        candidates = set()
        for cell in nearby_cells:
            candidates.update(self.cell_to_aircraft.get(cell, set()))

        results = []
        #print('candidates: ', candidates)
        for icao24 in candidates:
            data = self.r.hgetall(f"aircraft:{icao24}")
            distance = h3.great_circle_distance(
                (lat, lng),
                (float(data["latitude"]), float(data["longitude"])),
                unit="km"
            )
            if distance <= 100:
                results.append((icao24, data))

        #for result in results:
            #print(result)
        return results


'''import h3
from collections import defaultdict

# sample data
points = [
    {"id": 1, "lat": 45.7489, "lng": 21.2087},
    {"id": 2, "lat": 45.7500, "lng": 21.2100},
    {"id": 3, "lat": 45.8000, "lng": 21.3000},
]

resolution = 8

# build index
index = defaultdict(list)

for p in points:
    cell = h3.latlng_to_cell(p["lat"], p["lng"], resolution)
    index[cell].append(p)

# query point
center_lat, center_lng = 45.7489, 21.2087
center_cell = h3.latlng_to_cell(center_lat, center_lng, resolution)

# step 1: get candidate cells
k = 3
near_cells = h3.grid_disk(center_cell, k)

# step 2: gather candidates
candidates = []
for cell in near_cells:
    candidates.extend(index.get(cell, []))

# step 3: exact filter
radius_km = 2
results = [
    p for p in candidates
    if h3.great_circle_distance(
        (center_lat, center_lng),
        (p["lat"], p["lng"]),
        unit="km"
    ) <= radius_km
]

print(results)'''