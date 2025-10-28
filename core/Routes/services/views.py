import folium
from decimal import Decimal
from geopy.distance import geodesic
import requests

from django.conf import settings

from .views import *
from Tasker.models import *
from ..serializers import *


type LocationPoint = tuple[Decimal, Decimal]


def get_simple_distance(point1: LocationPoint, point2: LocationPoint) -> float:
    return geodesic(point1, point2).kilometers

def get_route_distance(points: list[LocationPoint]) -> float:
    distance = 0.0
    for i in range(len(points)-1):
        distance += get_simple_distance(points[i], points[i+1])

    return distance

def get_shortest_route(point1: LocationPoint, point2: LocationPoint, mode: str = 'foot-walking'):
    host, port = settings.ORS_HOST, settings.ORS_PORT
    base_url = f'http://{host}:{port}/ors/v2/directions'
    url = f'{base_url}/{mode}'
    params = {
        'start':f'{point1[1]},{point1[0]}',
        'end': f'{point2[1]},{point2[0]}'
    }

    response = requests.get(url, params=params)
    response = response.json()
    route_sequence = response \
        .get('features')[0] \
        .get('geometry') \
        .get('coordinates')
    
    route_sequence = [(route[1], route[0]) for route in route_sequence]

    return route_sequence

def calculate_zoom(point1, point2):
    z = 0
    d = get_route_distance([point1, point2])
    if d >= 15:
        z = 12
    elif 15 > d >= 7.5:
        z = 13
    else:
        z = 14

    return z

def show_route(shape_sequence: list[LocationPoint]) -> str:
    l = len(shape_sequence)
    fst_point, mdl_point, lst_point = shape_sequence[0], shape_sequence[l // 2], shape_sequence[-1]
    x1, x2, x3 = (p[0] for p in (fst_point, mdl_point, lst_point))
    y1, y2, y3 = (p[1] for p in (fst_point, mdl_point, lst_point))
    three = Decimal(3.0)
    center = (sum([x1, x2, x3]) / three, sum([y1, y2, y3]) / three)
    zoom = calculate_zoom(fst_point, lst_point)
    m = folium.Map(location=center, zoom_start=zoom)

    folium.PolyLine(
        locations=shape_sequence,
        color='red',
        weight=5,
        opacity=0.5
    ).add_to(m)

    for i, point in enumerate(shape_sequence):
        if i in {0, len(shape_sequence)-1}:
            folium.Marker(point, popup=f'Point {i+1}').add_to(m)

    return m._repr_html_()

def get_route(route_id:str) -> dict:
    route = Route.objects.get(route_id=route_id)
    route = RouteDetailsSerializer(route).data
    return route