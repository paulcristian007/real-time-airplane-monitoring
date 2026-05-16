class GeospatialIndex:
    def __init__(self):
        pass

    def store_metadata(self, metadata_key, callsign, latitude, longitude, velocity, altitude):
        pass

    def store_in_index(self, icao24, latitude, longitude):
        pass

    def is_stored_in_index(self, metadata_key):
        pass

    def create_backup(self):
        pass

    def fetch_coordinates(self):
        pass

    def fetch_metadata(self):
        pass

    def query_index(self, update_in_progress, latitude, longitude):
        pass

    def measure_memory_usage(self):
        pass