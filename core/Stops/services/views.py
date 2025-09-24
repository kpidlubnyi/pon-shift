from geopy.geocoders import Nominatim
from logging import getLogger
from collections import defaultdict
import heapq

from django.db.models.manager import BaseManager
from django.db.models import Q
from django.utils import timezone as tz

from ..exceptions import *
from Tasker.models.common import *
from ..serializers import *
from Routes.services.views import *


logger = getLogger(__name__)


def get_location(address: str) -> tuple[float ,float]:
    nominatim = Nominatim(user_agent='pon-shift')
    location = nominatim.geocode(f"{address}, Warsaw, Poland", exactly_one=True)

    if not location:
        raise AddressNotFoundError(f'Адресу {address} не знайдено!')
    return (location.latitude, location.longitude)

def get_n_nearest_points(selfpoint: tuple[float, float], dataset: list[Stop], n: int) -> list:
    if n > len(dataset):
        raise ValueError('Не можна зробити вибірку більшу ніж увесь набір!')
    
    distances = []
    
    for stop in dataset:
        point = stop.get_coordinates()
        distance = get_simple_distance(selfpoint, point)
        distances.append((distance, stop))
    
    n_smallest = heapq.nsmallest(n, distances, key=lambda x: x[0])
    
    result = [(StopBriefSerializer(stop).data, distance) for distance, stop in n_smallest]
    return result

def get_nearest_stops(location: str | tuple[float, float], stops: list[Stop], limit: int) -> list[dict]:    
    def format_distance(distance: float) -> str:
        if distance < 1:
            return f'{int(distance*1000)}m'
        elif distance < 10:
            return f'{round(distance, 2)}km'
        else:
            return f'{round(distance, 1)}km'
    
    if isinstance(location, str):
        location = get_location(location)
    
    nearest_points = get_n_nearest_points(location, stops, limit)
    nearest_stops = []
    
    for stop_data, distance in nearest_points:
        nearest_stops.append({
            'stop': stop_data,
            'distance': format_distance(distance),
        })
    
    return nearest_stops

def intercept_bad_stop_id(stop_id: str) -> str:
    """Функція перехоплює індески станцій метро, котрі не з'являються в маршрутах, та повертає валідний."""
    def get_stop_by_id():
        nonlocal stop_id
        return Stop.objects.get(stop_id=stop_id)

    stop = get_stop_by_id()

    if stop.location_type in [1,2]:
        stop_id = stop_id.split(':')[0] + ':P1'

        try:
            stop = get_stop_by_id()
        except Stop.DoesNotExist:
            stop_id = stop_id[:-1] + '2' 
            stop = get_stop_by_id()

    good_stop_id = stop.stop_id

    return good_stop_id

def get_available_routes(stoptime_objs: BaseManager[StopTime]) -> list[str]:
    """Повертає список курсів, котрі зупиняються на цій зупинці, основуючись на відфільтрованному по потрібній зупинці датасеті зупинок транспорту."""
    trips_of_stop = stoptime_objs \
    .distinct('trip__trip_id') \
    .values_list('trip__trip_id', flat=True)

    available_routes = Route.objects \
        .filter(trip__trip_id__in=trips_of_stop) \
        .distinct('route_id') \
        .values_list('route_id', flat=True)
    
    return list(available_routes)


d = defaultdict(lambda: 'PcS')
d.update({5:'PtS', 6:'SbS', 7:'NdS'})


def get_recent_trips(carrier:str, stoptime_objs: BaseManager[StopTime], n: int = 10, datetime = tz.localtime(tz.now())):
    day_of_week = datetime.isoweekday()
    date, time = datetime.date(), datetime.time()

    match carrier:
        case 'ZTM':
            trip_filter = (
                Q(trip__trip_id__contains=date) & 
                Q(trip__trip_id__contains=d[day_of_week])
            )
        case 'WKD':
            carrier = Carrier.objects.get(carrier_code=carrier)
            excluded_services = CalendarDate.objects \
                .filter(carrier=carrier, date=date) \
                .values_list('service_id', flat=True)
            trip_filter = ~Q(trip__service_id__in=excluded_services)
            
    stoptime_objs = stoptime_objs \
        .filter(trip_filter) \
        .filter(arrival_time__gt=time) \
        .order_by('arrival_time')[:n]

    recent_trips = []

    for stop_time in stoptime_objs:
        route = stop_time.trip.route.route_short_name
        stop_time = RecentTripStopTimeSerializer(stop_time).data
        stop_time['route'] = route
        recent_trips.append(stop_time)

    return recent_trips
