import copy
class GeospatialIndex:
    def __init__(self):
        pass
        self.metadata = {}
        self.new_metadata = {}


    def load_in_memory(self):
        pass

    def update_cache(self):
        self.metadata = copy.deepcopy(self.new_metadata)


    def refine_aircraft_data(self, raw_aircraft):
        icao24 = raw_aircraft[0]
        callsign = raw_aircraft[1]
        longitude = raw_aircraft[5]
        latitude = raw_aircraft[6]
        on_ground = raw_aircraft[8]
        velocity = raw_aircraft[9]
        altitude = raw_aircraft[13]

        # Ignore invalid coordinates
        if latitude is None or longitude is None:
            return None, None
        if velocity is not None:
            velocity = self.convert_speed_to_knots(float(velocity))
        else:
            velocity = 0
        if altitude is not None:
            altitude = round(self.convert_altitude_to_feet(float(altitude)))
        else:
            altitude = 0

        aircraft = {
            'callsign': callsign,
            'longitude': longitude,
            'latitude': latitude,
            'on_ground': on_ground,
            'velocity': velocity,
            'altitude': altitude
        }
        return icao24, aircraft


    def process_aircrafts(self, aircrafts, quasi_static_optimization=False, update_optimization=False, add_optimization=False):
        transaction = self.init_transaction()
        self.new_metadata = {}
        updateCount = 0
        indexCount = 0
        for raw_aircraft in aircrafts:
            icao24, aircraft = self.refine_aircraft_data(raw_aircraft)
            if aircraft is None:
                continue
            aircraft['cell'] = self.get_cell(aircraft)
            self.new_metadata[icao24] = aircraft
            indexCount += self.store_in_index(transaction, icao24, aircraft, quasi_static_optimization, add_optimization)
            fields = self.get_fields_to_update(icao24, aircraft, quasi_static_optimization, update_optimization)
            updateCount += len(fields.keys())
            if len(fields.keys()) > 0:
                self.store_metadata(transaction, icao24, fields)

        '''print('metadata: ')
        for key in self.metadata:
            print(self.metadata[key])'''
        self.remove_finished_aircrafts(transaction)
        self.update_cache()
        self.run_transaction(transaction)
        return updateCount, indexCount


    def remove_finished_aircrafts(self, transaction):
        pass

    def run_transaction(self, transaction):
        pass

    def init_transaction(self):
        pass

    def store_metadata(self, transaction, icao24, fields):
        pass

    def store_in_index(self, transaction, icao24, aircraft, quasi_static_optimization, add_optimization):
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
        return round(float(velocity) * 1.94384)


    def convert_altitude_to_feet(self, altitude):
        return round(float(altitude) * 3.28084)

    def get_fields_to_update(self, icao24, aircraft, quasi_static_optimization=False, update_optimization=False):
        if icao24 in self.metadata and quasi_static_optimization and aircraft['on_ground']:
            return {}

        if icao24 not in self.metadata or not update_optimization:
            fields = {
                'callsign': aircraft['callsign'],
                'latitude': aircraft['latitude'],
                'longitude': aircraft['longitude'],
                'velocity': aircraft['velocity'],
                'altitude': aircraft['altitude']
            }
            return fields

        fields = {
            'latitude': aircraft['latitude'],
            'longitude': aircraft['longitude']
        }

        if not aircraft['velocity'] == self.metadata[icao24]['velocity']:
            fields['velocity'] = aircraft['velocity']
        if not aircraft['altitude'] == self.metadata[icao24]['altitude']:
            fields['altitude'] = aircraft['altitude']
        return fields

    def get_cell(self, aircraft):
        return None
