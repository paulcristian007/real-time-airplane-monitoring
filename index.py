class GeospatialIndex:
    def __init__(self):
        pass
        self.metadata = {}


    def load_in_memory(self):
        pass

    def process_aicrafts(self, aircrafts_chunk, optimizer=False, quasi_static=False):
        pass


    def store_metadata(self, metadata_key, callsign, latitude, longitude, velocity, altitude):
        pass

    def store_in_index(self, icao24, latitude, longitude):
        pass

    def is_stored_in_index(self, metadata_key):
        return metadata_key in self.metadata

    def create_backup(self):
        pass

    def fetch_coordinates(self):
        pass

    def fetch_metadata(self):
        pass

    def query_index(self, update_in_progress, latitude, longitude):
        pass

    def get_memory_usage(self):
        return 0, 0

    def convert_speed_to_knots(self, velocity):
        return velocity * 1.94384

    def convert_altitude_to_feet(self, altitude):
        return altitude * 3.28084