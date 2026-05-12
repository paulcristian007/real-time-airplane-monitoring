import threading
import time
import requests
import redis
import queue


OPENSKY_URL = "https://opensky-network.org/api/states/all"
POLL_INTERVAL = 10

REDIS_HOST = "localhost"
REDIS_PORT = 6379

REDIS_GEO_KEY = "aircraft_positions"

# -----------------------------
# Redis connection
# -----------------------------

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

aircraft_queue = queue.Queue()

def convert_speed_to_knots(velocity):
    return velocity * 1.94384

def convert_altitude_to_feet(altitude):
    return altitude * 3.28084
def is_quasi_static_object(velocity):
    if velocity is None:
        return 1
    return velocity < 100.0

def fetch_opensky():
    try:
        response = requests.get(
            OPENSKY_URL,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            states = data.get("states", [])
            print(f"Fetched {len(states)} aircraft")
            for aircraft in states:
                aircraft_queue.put(aircraft)

        else:
            print("OpenSky error:", response.status_code)

    except Exception as e:
        print("Polling error:", e)
   # time.sleep(max(0, POLL_INTERVAL))


def process_aircraft():
    while aircraft_queue.empty() is not True:
        aircraft = aircraft_queue.get()
        icao24 = aircraft[0]
        callsign = aircraft[1]

        longitude = aircraft[5]
        latitude = aircraft[6]

        velocity = aircraft[9]
        if velocity is not None:
            velocity = convert_speed_to_knots(float(velocity))

        altitude = aircraft[13]
        if altitude is not None:
            altitude = convert_altitude_to_feet(float(altitude))

        # Ignore invalid coordinates
        if latitude is None or longitude is None:
            continue

        if is_quasi_static_object(velocity):
            continue

        r.geoadd(
            REDIS_GEO_KEY,
            (longitude, latitude, icao24)
        )

        metadata_key = f"aircraft:{icao24}"
        r.hset(metadata_key, mapping={
            "callsign": callsign or "",
            "latitude": latitude,
            "longitude": longitude,
            "velocity": velocity or 0,
            "altitude": altitude or 0,
            "last_update": int(time.time())
        })
#longitude = 23.59,
#latitude = 46.77,

def nearby_aircraft_monitor():
    try:
        nearby = r.geosearch(
            REDIS_GEO_KEY,
            longitude=23.59,
            latitude=46.77,
            radius=100,
            unit="km"
        )

        print(
            f"Aircraft near Istanbul: {len(nearby)}"
        )
        for icao24 in nearby:
            details = r.hgetall(f"aircraft:{icao24}")
            print(icao24, details)

    except Exception as e:
        print("Query error:", e)


for _ in range(10):
    start = time.perf_counter()
    fetch_opensky()
    workers = []
    for _ in range(8):
        workers.append(threading.Thread(
            target=process_aircraft,
            daemon=True
        ))
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    end = time.perf_counter()
    print(f"Processing time: {end - start:.4f} seconds")
    nearby_aircraft_monitor()
    time.sleep(10)
