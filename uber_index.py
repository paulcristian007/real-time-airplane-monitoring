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
        self.locks = [Lock() for _ in range(64)]
        REDIS_HOST = "localhost"
        REDIS_PORT = 6379
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
        self.r.flushall()

    def reset(self):
        self.r.flushall()

    def is_stored_in_index(self, metadata_key):
        return False
        #return self.r.exists(f"aircraft:{metadata_key}")

    def store_metadata(self, metadata_key, callsign, latitude, longitude, velocity, altitude):
        metadata_key = f"aircraft:{metadata_key}"
        self.r.hset(metadata_key, mapping={
            "callsign": callsign or "",
            "latitude": latitude,
            "longitude": longitude,
            "velocity": velocity or 0,
            "altitude": altitude or 0,
        })

    def store_in_index(self, icao24, latitude, longitude):
        cell = h3.latlng_to_cell(latitude, longitude, self.resolution)
        lock = self.locks[hash(cell) % 64]
        lock.acquire()
        self.cell_to_aircraft[cell].add(icao24)
        lock.release()
        return cell


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