from pymongo import MongoClient, GEOSPHERE, UpdateOne
import time

from index import GeospatialIndex


class MongoDbIndex(GeospatialIndex):

    def __init__(self):
        super().__init__()

        MONGO_URI = "mongodb://localhost:27017"

        self.client = MongoClient(MONGO_URI)
        self.client.drop_database("aircraft_db")
        self.client.drop_database("aircraft_positions_backup")
        self.db = self.client["aircraft_db"]
        self.collection = self.db["aircraft_positions"]
        self.backup_collection = self.db["aircraft_positions_backup"]


        # Create geospatial index
        self.collection.create_index(
            [("location", GEOSPHERE)]
        )
        self.collection.create_index("icao24", unique=True)

        self.backup_collection.create_index(
            [("location", GEOSPHERE)]
        )
        self.bulk_operations = []


    def store_in_index(self, transaction, icao24, aircraft, quasi_static_optimization, add_optimization):
        if icao24 in self.metadata and aircraft['on_ground'] and quasi_static_optimization:
            return 0
        transaction.append(UpdateOne(
            {"icao24": icao24},
            {
                "$set": {
                    "icao24": icao24,
                    "location": {
                        "type": "Point",
                        "coordinates": [
                            aircraft['longitude'],
                            aircraft['latitude']
                        ]
                    }
                }
            },
            upsert=True))
        return 1

    def init_transaction(self):
        return []


    def run_transaction(self, transaction):
        self.collection.bulk_write(transaction, ordered=False)

    def store_metadata(self, transaction, icao24, fields):
        transaction.append(UpdateOne(
            {"icao24": icao24},
            {
                "$set": fields
            },
            upsert=True))

    '''def is_stored_in_index(self, metadata_key):
        return self.collection.find_one(
            {"icao24": metadata_key},
            {"_id": 1}
        ) is not None'''

        #return self.collection.count_documents({"icao24": metadata_key}, limit=1) > 0


    def create_backup(self):
        t0 = time.perf_counter()
        self.backup_collection.delete_many({})
        docs = list(self.collection.find())
        if docs:
            self.backup_collection.insert_many(docs)
        t1 = time.perf_counter()
        print(
            f"Backup time: "
            f"{t1 - t0:.4f} seconds"
        )


    def nearby_aircraft_monitor(self, update_in_progress):
        try:

            collection = self.collection

            if update_in_progress:
                collection = self.backup_collection

            nearby = collection.find({
                "location": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [
                                28.72,
                                41.27
                            ]
                        },
                        "$maxDistance": 100000
                    }
                }
            })

            nearby_list = list(nearby)
            results = []
            for aircraft in nearby_list:
                #icao = nearby.get("icao24")
                #print(nearby)
                #aircraft = self.collection.find_one({"icao24": icao})
                #aircraft["location"]["coordinates"][1],
                results.append({
                        "callsign":
                            aircraft["callsign"],

                        "latitude":
                            aircraft["latitude"],

                        "longitude":
                            aircraft["longitude"],

                        "velocity":
                            aircraft["velocity"],

                        "altitude":
                            aircraft["altitude"]
                    })
            return results
        except Exception as e:
            print("Query error:", e)

    def get_memory_usage(self):
        self.client.admin.command("fsync")
        stats = self.db.command("collStats", "aircraft_positions")
        print(stats["indexSizes"])
        megabyte_size = 1024 * 1024
        index_size = stats["indexSizes"]["location_2dsphere"] / megabyte_size
        metadata_size = (stats["indexSizes"]["_id_"] + stats["indexSizes"]["icao24_1"]) / megabyte_size
        return index_size, metadata_size
