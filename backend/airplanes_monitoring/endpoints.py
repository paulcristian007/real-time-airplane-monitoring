from rest_framework.decorators import api_view
from rest_framework.response import Response
import csv
import os

from django.apps import apps


@api_view(["GET"])
def get_airports(request):
    csv_file = os.path.join(os.path.dirname(__file__), 'airports.csv')
    try:
        airports = []

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                airport = {
                    "id": row["id"],
                    "name": row["name"],
                    "iata": row.get("iata_code") or None,
                    "icao": row.get("ident") or None,
                    "lat": float(row["latitude_deg"]),
                    "lon": float(row["longitude_deg"]),
                    "city": row.get("municipality") or None,
                    "country": row.get("iso_country") or None,
                }

                airports.append(airport)
        response_json = {
            "items": airports
        }
        return Response(response_json, status=200)
    except Exception as e:
        print(str(e))
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_nearby_airplanes(request):
    try:
        lng = float(request.GET.get("lng"))
        lat = float(request.GET.get("lat"))
        config = apps.get_app_config("airplanes_monitoring")
        response_json = config.index.nearby_aircraft_monitor(lng, lat, config.update)
        return Response(response_json, status=200)
    except Exception as e:
        print(str(e))
        return Response({"error": str(e)}, status=500)


