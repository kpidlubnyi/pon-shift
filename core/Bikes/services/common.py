import requests

from routes.services.views import *

def find_bike_stations_nearby(location: tuple[float, float], radius: int = 200, limit: int = 5):
    def is_private(station):
        tags = station.get('tags')

        if tags and 'access' in tags.keys():
            return True if tags['access'] == 'private' else False

        return False

    def add_coordinates_to_way_station(station: dict) -> tuple[float, float]:
        min_lat, min_lon, max_lat, max_lon = station.get('bounds').values()
        station['lat'] = (min_lat + max_lat) / 2.0
        station['lon'] = (min_lon + max_lon) / 2.0
        return station

    def filter_station_data(station: dict) -> dict:
        tags: dict = station.get('tags')

        if not tags:
            raise ValueError()

        capacity = tags.get('capacity')
        covered = tags.get('covered')

        if not (capacity and covered):
            raise ValueError()

        result = {
            'lat': station.get('lat'),
            'lon': station.get('lon'),
            'capacity': capacity,
            'covered': covered,
        }

        return result

    lat, lon = location
    response = requests.post(
        url='https://overpass-api.de/api/interpreter',
        data=f"""
            [out:json][timeout:10];
            (
                node["amenity"="bicycle_parking"](around:{radius},{lat},{lon});
                way["amenity"="bicycle_parking"](around:{radius},{lat},{lon});
            );
            out;
        """
    )

    response.raise_for_status()
    data = response.json().get('elements')
    stations = []

    for station in data:
        if is_private(station):
            continue

        if station.get('type') == 'way':
            station = add_coordinates_to_way_station(station)

        try:
            station = filter_station_data(station)
        except:
            continue

        station_location = (station['lat'], station['lon'])
        route = calculate_simple_distance([location, station_location])
        station['distance'] = route

        stations.append(station)

    stations = sorted(stations,key=lambda x: x['distance'])[:limit]

    for station in stations:
        station_location = (station['lat'], station['lon'])
        route_to_station = get_shortest_route(location, station_location)
        station['distance'] = round(calculate_simple_distance(route_to_station), 3)

    stations = sorted(stations,key=lambda x: x['distance'])
    return stations
