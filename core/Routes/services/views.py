from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from Tasker.models import *


def get_location(address: str) -> tuple[float ,float]:
    nominatim = Nominatim(user_agent='pon-shift')

    location = nominatim.geocode(f"{address}, Warsaw, Poland")

    if location:
        return (location.latitude, location.longitude)
    return None

def get_distance(point1: tuple[float, float], point2: tuple[float, float]) -> float:
    return geodesic(point1, point2).kilometers

def get_n_nearest_points(selfpoint: tuple[float, float], dataset: list[Stop], n: int) -> list:
    def add_to_list(stop_id, distance):
        nonlocal result, n

        for i in range(n):
            if distance < result[i][1]:
                position = i
                break
        
        result[position+1:] = result[position:-1]
        result[position] = stop_id, distance

    if n > len(dataset):
        return ValueError('Не можна зробити вибірку більшу ніж увесь набір!')
    result = [(_, float('inf')) for _ in range(n)]

    for stop in dataset:
        point = stop.get_coordinates()
        distance = get_distance(selfpoint, point)
        
        if distance < result[n-1][1]:
            add_to_list(str(stop), distance)

    return result

def get_n_nearest_stops(location, limit):
    def format_distance(distance: float) -> str:
        if distance < 1:
            return f'{int(distance*1000)}m'
        elif distance < 10:
            return f'{round(distance,2)}km'
        else:
            return f'{round(distance, 1)}km'
        
    selfpoint = get_location(location)
    stops = Stop.objects.all()

    nearest_points = get_n_nearest_points(selfpoint, stops, limit)
    nearest_stops = {
        point[0]: format_distance(point[1])
        for point in nearest_points
    }

    return nearest_stops

