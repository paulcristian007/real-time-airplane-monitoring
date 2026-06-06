from django.urls import path

from .endpoints import get_nearby_airplanes, get_airports


urlpatterns = [
    path('fetch_airports/', get_airports, name='get_airports'),
    path('nearby_aircrafts', get_nearby_airplanes, name='get_nearby_airplanes')
]