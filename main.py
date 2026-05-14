import threading
import time
import requests
import redis
import queue
from dotenv import load_dotenv
import os


def get_open_sky_api_token():
    load_dotenv()
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")

    response = requests.post(
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    )
    token = response.json()["access_token"]
    return token


OPENSKY_URL = "https://opensky-network.org/api/states/all"
POLL_INTERVAL = 10

REDIS_HOST = "localhost"
REDIS_PORT = 6379

REDIS_GEO_KEY = "aircraft_positions"
REDIS_ICAO_INDEX = "aicraft_icao"

# -----------------------------
# Redis connection
# -----------------------------

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)
r.flushall()

aircraft_queue = queue.Queue()


def convert_speed_to_knots(velocity):
    return velocity * 1.94384


def convert_altitude_to_feet(altitude):
    return altitude * 3.28084


def is_quasi_static_object(velocity):
    if velocity is None:
        return 1
    return velocity < 100.0


token = None


def fetch_opensky(token=None):
    try:
        if token is None:
            get_open_sky_api_token()
        headers = {
            "Authorization": f"Bearer {get_open_sky_api_token()}"
        }
        response = requests.get(
            OPENSKY_URL,
            headers=headers,
            timeout=10
        )
        print("Tokens left: ", response.headers.get("X-Rate-Limit-Remaining"))
        if response.status_code == 200:
            data = response.json()
            states = data.get("states", [])
            print(f"Fetched {len(states)} aircraft")
            count = 0
            for aircraft in states:
                aircraft_queue.put(aircraft)
                if aircraft[8]:
                    count += 1

            print('stopped: ', count)
        else:
            print("OpenSky error:", response.status_code)

    except Exception as e:
        print("Polling error:", e)


# time.sleep(max(0, POLL_INTERVAL))


lock = threading.Lock()
count = 0


def process_aircraft():
    while aircraft_queue.empty() is not True:
        aircraft = aircraft_queue.get()
        icao24 = aircraft[0]
        callsign = aircraft[1]

        longitude = aircraft[5]
        latitude = aircraft[6]
        on_ground = aircraft[8]
        velocity = aircraft[9]
        if velocity is not None:
            velocity = convert_speed_to_knots(float(velocity))
        altitude = aircraft[13]
        if altitude is not None:
            altitude = convert_altitude_to_feet(float(altitude))

        # Ignore invalid coordinates
        if latitude is None or longitude is None:
            continue

        metadata_key = f"aircraft:{icao24}"
        r.hset(metadata_key, mapping={
            "callsign": callsign or "",
            "latitude": latitude,
            "longitude": longitude,
            "velocity": velocity or 0,
            "altitude": altitude or 0,
        })
        if not on_ground:
            r.geoadd(
                REDIS_GEO_KEY,
                (longitude, latitude, icao24)
            )


        # longitude = 23.59,
# latitude = 46.77,

def nearby_aircraft_monitor():
    try:
        nearby = r.geosearch(
            REDIS_GEO_KEY,
            longitude=28.72,
            latitude=41.27,
            radius=100,
            unit="km"
        )

        print(
            f"Aircraft near Cluj: {len(nearby)}"
        )
        for icao24 in nearby:
            details = r.hgetall(f"aircraft:{icao24}")
            print(icao24, details)

    except Exception as e:
        print("Query error:", e)


for _ in range(5):
    start = time.perf_counter()
    fetch_opensky()
    workers = []
    for _ in range(12):
        workers.append(threading.Thread(
            target=process_aircraft,
            daemon=True
        ))
    for worker in workers:
        worker.start()

    # put queries here -> taking place during an update operation
    for worker in workers:
        worker.join()

    end = time.perf_counter()
    print(f"Processing time: {end - start:.4f} seconds")

    start = time.perf_counter()
    nearby_aircraft_monitor()
    end = time.perf_counter()
    print(f"Query time: {end - start:.4f} seconds")
    time.sleep(10)
