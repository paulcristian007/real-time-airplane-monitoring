import threading
import time
import csv
import requests
import queue
from datetime import datetime
from dotenv import load_dotenv

from mongodb_index import MongoDbIndex
from redis_index import RedisIndex
from postgis_index import PostGISIndex
from uber_index import UberIndex
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

aircraft_queue = queue.Queue()


def is_quasi_static_object(velocity):
    if velocity is None:
        return 1
    return velocity < 100.0


def fetch_opensky(token, no_aircrafts=None):
    try:
        headers = {
            "Authorization": f"Bearer {token}"
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
            totalCount = 0
            aircrafts = []
            for aircraft in states:
                aircrafts.append(aircraft)
                if aircraft[8]:
                    count += 1
                totalCount += 1
                if no_aircrafts and totalCount == no_aircrafts:
                    break

            while totalCount < no_aircrafts:
                for aircraft in states:
                    aircraft[0] += '#'
                    if aircraft[8]:
                        count += 1
                    aircrafts.append(aircraft)
                    totalCount += 1
                    if no_aircrafts and totalCount == no_aircrafts:
                        break
            print(totalCount)
            print('stopped: ', count)
            return aircrafts
        else:
            print("OpenSky error:", response.status_code)
            return None

    except Exception as e:
        print("Polling error:", e)
        return None
def process_aircrafts(index, aircrafts_chunk):
    index.process_aicrafts(aircrafts_chunk)
    '''for aircraft in aircrafts_chunk:
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

        #metadata_key = f"aircraft:{icao24}"
        metadata_key = icao24
        if not on_ground or not index.is_stored_in_index(metadata_key):
            index.store_in_index(icao24, latitude, longitude)
        index.store_metadata(metadata_key, callsign, latitude, longitude, velocity, altitude)'''

        # longitude = 23.59,
# latitude = 46.77,

def run_experiments():
    iterations = 10
    no_aircrafts = [50000]#, 10000, 25000, 50000]
    index_type = 'uber'
    experiments_loop(iterations, no_aircrafts, index_type)


def experiments_loop(iterations, no_aircrafts, index_type):
    results = []
    token = get_open_sky_api_token()
    for no_aircraft in no_aircrafts:
        execution_times = []
        index = None
        if index_type == 'redis':
            index = RedisIndex()
        elif index_type == 'mongodb':
            index = MongoDbIndex()
        elif index_type == 'postgis':
            index = PostGISIndex()
        else:
            index = UberIndex()
        for i in range(iterations + 1):
            fetch_opensky(token=token, no_aircrafts=no_aircraft)
            aircrafts = fetch_opensky(token, no_aircrafts=no_aircraft)
            start = time.perf_counter()
            index.load_in_memory()
            process_aircrafts(index, aircrafts)
            end = time.perf_counter()
            if i > 0:
                execution_times.append(end - start)
            print(f"Processing time: {end - start:.4f} seconds")

        avg_time = sum(execution_times) / len(execution_times)
        #index_size, metadata_size = index.get_memory_usage()
        results.append((no_aircraft, f"{avg_time:.2f} s"))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    with open(f"./experiments/{index_type}_results_{timestamp}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["aircrafts", "average time"])
        writer.writerows(results)


def run_query_experiments():
    no_aircrafts = [5000, 7500, 10000, 11500]
    no_queries = [1000, 5000, 10000]
    index_type = 'postgis'
    experiments_query_loop(12, no_aircrafts, no_queries, index_type)

def run_queries(index, no_queries):
    #print(no_queries)
    for _ in range(no_queries):
        index.nearby_aircraft_monitor(update_in_progress=False)

def experiments_query_loop(no_threads, no_aircrafts, no_queries, index_type):
    results = []
    token = get_open_sky_api_token()
    for no_aircraft in no_aircrafts:
        for queries in no_queries:
            index = None
            if index_type == 'redis':
                index = RedisIndex()
            elif index_type == 'mongodb':
                index = MongoDbIndex()
            elif index_type == 'postgis':
                index = PostGISIndex()
            else:
                index = UberIndex()
            workers = []
            fetch_opensky(token=token, no_aircrafts=no_aircraft)
            process_aircraft(index)

            for _ in range(no_threads):
                workers.append(threading.Thread(
                    target=run_queries,
                    args=(index, int(queries / no_threads)),
                    daemon=True
                ))

            start = time.perf_counter()
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
            end = time.perf_counter()
            results.append((no_aircraft, queries, f"{end - start:.2f} s"))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    with open(f"./experiments/{index_type}_query_results_{timestamp}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["aircrafts", "queries", "average query time"])
        writer.writerows(results)


def main():
    token = get_open_sky_api_token()
    no_thread = 1
    index = UberIndex()
    for _ in range(5):
        aircrafts = fetch_opensky(token, no_aircrafts=5000)
        start = time.perf_counter()
        index.load_in_memory()
        process_aircrafts(index, aircrafts)
        end = time.perf_counter()
        print(f"Processing time: {end - start:.4f} seconds")

        start = time.perf_counter()
        #index.nearby_aircraft_monitor(update_in_progress=False)
        end = time.perf_counter()
        print(f"Query time: {end - start:.4f} seconds")
        #index.create_backup()
        time.sleep(2)

main()
#run_experiments()
#run_query_experiments()
