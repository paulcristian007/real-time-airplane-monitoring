from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import requests

from .uber_index import UberIndex

OPENSKY_URL = "https://opensky-network.org/api/states/all"




class AirplanesMonitoringConfig(AppConfig):
    name = "airplanes_monitoring"

    def get_open_sky_api_token(self):
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
    def fetch_opensky(self, token):
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
                print(totalCount)
                print('stopped: ', count)
                return aircrafts
            else:
                print("OpenSky error:", response.status_code)
                return None

        except Exception as e:
            print("Polling error:", e)
            return None

    def update_states(self, index, token):
        aircrafts = self.fetch_opensky(token)
        index.process_aircrafts(aircrafts, quasi_static_optimization=True, update_optimization=True,
                                add_optimization=True)
    def ready(self):
        token = self.get_open_sky_api_token()
        self.index = UberIndex()
        self.update = False
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.update_states, "interval", seconds=5, args=[self.index, token])
        scheduler.start()