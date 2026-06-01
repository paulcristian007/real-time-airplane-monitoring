import threading
import time
import csv
from copy import deepcopy

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

            idd = 0
            while totalCount < no_aircrafts:
                idd += 1
                for aircraft in states:
                    new_aircraft = deepcopy(aircraft)
                    new_aircraft[0] = aircraft[0] + f'#{idd}'
                    if aircraft[8]:
                        count += 1
                    aircrafts.append(new_aircraft)
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



        # longitude = 23.59,
# latitude = 46.77,

def run_experiments():
    iterations = 10
    no_aircrafts = [5000, 7500, 10000, 11500, 25000]
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
        for i in range(iterations):
            aircrafts = fetch_opensky(token, no_aircrafts=no_aircraft)
            start = time.perf_counter()
            index.process_aircrafts(aircrafts, quasi_static_optimization=True, update_optimization=True,
                                    add_optimization=False)
            end = time.perf_counter()
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
    no_aircrafts = [25000, 50000]
    no_queries = [1000]
    index_type = 'redis'
    experiments_query_loop(12, no_aircrafts, no_queries, index_type)

def run_queries(index, no_queries):
    for _ in range(no_queries):
        index.nearby_aircraft_monitor(update_in_progress=False)

def experiments_update_loop(iterations, no_aircrafts, update_states):
     results = []
     token = get_open_sky_api_token()
     for no_aircraft in no_aircrafts:
         for i in range(1):
             execution_times = []
             quasi = update_states[i][0]
             update = update_states[i][1]
             add = update_states[i][2]
             index = UberIndex()

             updateCounts = []
             indexCounts = []
             for i in range(iterations):
                 aircrafts = fetch_opensky(token, no_aircrafts=no_aircraft)
                 start = time.perf_counter()
                 updateCount, indexCount = index.process_aircrafts(aircrafts, quasi_static_optimization=quasi, update_optimization=update,
                                         add_optimization=add)
                 end = time.perf_counter()
                 execution_times.append(end - start)
                 updateCounts.append(updateCount)
                 indexCounts.append(indexCount)
                 print(f"Processing time: {end - start:.4f} seconds")

             avg_time = sum(execution_times) / len(execution_times)
             avg_update_count = sum(updateCounts) // len(updateCounts)
             avg_index_count = sum(indexCounts) // len(indexCounts)
             # index_size, metadata_size = index.get_memory_usage()
             results.append((no_aircraft, f"{avg_time:.2f} s", quasi, update, add, avg_update_count, avg_index_count))

         timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
         with open(f"./experiments/update_optimizations_{timestamp}.csv", "w", newline="") as f:
             writer = csv.writer(f)
             writer.writerow(["aircrafts", "average time", "quasi-static", "update", "geoadd", "update count", "geoadd_count"])
             writer.writerows(results)

def run_update_count_experiments():
    no_aircrafts = [10000, 25000, 50000]
    states = [[True, True, True]] #[[False, False, False], [True, False, False], [True, True, False], [True, True, True]]
    experiments_update_loop(10, no_aircrafts, states)

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
            aircrafts = fetch_opensky(token=token, no_aircrafts=no_aircraft)
            index.process_aircrafts(aircrafts, quasi_static_optimization=True, update_optimization=True,
                                    add_optimization=False)

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

def run_memory_experiments():
    no_aircrafts = [5000, 11500, 25000, 50000]#, 25000, 50000]
    index_type = 'mongodb'
    experiments_memory(no_aircrafts, index_type)

def experiments_memory(no_aircrafts,index_type):
    results = []
    token = get_open_sky_api_token()
    for no_aircraft in no_aircrafts:
            index = None
            if index_type == 'redis':
                index = RedisIndex()
            elif index_type == 'mongodb':
                index = MongoDbIndex()
            elif index_type == 'postgis':
                index = PostGISIndex()
            else:
                index = UberIndex()
            aircrafts = fetch_opensky(token=token, no_aircrafts=no_aircraft)
            index.process_aircrafts(aircrafts, quasi_static_optimization=True, update_optimization=True,
                                    add_optimization=False)
            index_size, metadata_size = index.get_memory_usage()
            results.append((no_aircraft, f"{index_size:.2f} MB", f"{metadata_size:.2f} MB"))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    with open(f"./experiments/{index_type}_memory_results_{timestamp}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["aircrafts", "index size", "metadata size"])
        writer.writerows(results)
def main():
    token = get_open_sky_api_token()
    aircrafts = fetch_opensky(token, no_aircrafts=10000)
    for i in range(5):
        index = UberIndex()
        start = time.perf_counter()
        #index.load_in_memory()
        updateCount, indexCount = index.process_aircrafts(aircrafts, quasi_static_optimization=True, update_optimization=True, add_optimization=False)
        end = time.perf_counter()

        print(f"Number of updates: {updateCount}")
        print(f"Number of ops in index: {indexCount}")

        print(f"Processing time: {end - start:.4f} seconds")

        start = time.perf_counter()
        index.nearby_aircraft_monitor(update_in_progress=False)
        end = time.perf_counter()
        print(f"Query time: {end - start:.4f} seconds")
        #index.create_backup()
        time.sleep(5)

#main()
#run_experiments()
#run_update_count_experiments()
#run_query_experiments()

run_memory_experiments()
