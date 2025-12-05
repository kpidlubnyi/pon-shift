from geopy.geocoders import Nominatim
from logging import getLogger
import heapq

from django.db.models.manager import BaseManager
from django.db.models import Q
from django.utils import timezone as tz

from common.services.common import *
from common.models.common import *
from Routes.services.views import *
from Routes.serializers import *
from ..exceptions import *
from ..serializers import *



logger = getLogger(__name__)


def get_location(address: str) -> tuple[float ,float]:
    nominatim = Nominatim(user_agent='pon-shift')
    location = nominatim.geocode(f"{address}, Warsaw, Poland", exactly_one=True)

    if not location:
        raise AddressNotFoundError(f'Address {address} was not found!')
    return (location.latitude, location.longitude)

def get_n_nearest_points(selfpoint: tuple[float, float], dataset: list[Stop], n: int) -> list:
    if n > len(dataset):
        raise ValueError('Cannot make a sample larger than the entire set!')
    
    distances = []
    for stop in dataset:
        point = stop.get_coordinates()
        distance = calculate_simple_distance([selfpoint, point])
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
    """The function intercepts the indices of metro stations that do not appear in the routes and returns a valid one."""
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

def get_available_routes(stoptime_objs: BaseManager[StopTime]) -> list[dict]:
    """Returns a list of routes that stop at this stop, based on the filtered dataset of transport stops for the required stop.."""
    trips_of_stop = stoptime_objs \
    .distinct('trip__trip_id') \
    .values_list('trip__trip_id', flat=True)

    available_routes = Route.objects \
        .filter(trip__trip_id__in=trips_of_stop) \
        .distinct('route_id')
    
    return RouteBriefSerializer(available_routes, many=True).data


def get_recent_trips(carrier:str, stoptime_objs: BaseManager[StopTime], n: int = 10, datetime = tz.localtime(tz.now())):
    day_of_week = datetime.isoweekday()
    date, time = datetime.date(), datetime.time()

    match carrier:
        case 'WTP':
            trip_filter = (
                Q(trip__trip_id__contains=date) & 
                Q(trip__trip_id__contains=get_wtp_weekday(day_of_week))
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

def add_carrier_data(stop: dict):
    carrier = stop['carrier']
    return CarrierSerializer(carrier).data

def extended_info(stop: dict) -> tuple[list[str], str]:
    stop_id = intercept_bad_stop_id(stop['stop_id'])

    if stop_id == '7014M:P1':
        stop_ids = [stop_id, stop_id[:-1]+'2']
    else:
        stop_ids = [stop_id]
    
    stoptime_objs = StopTime.objects.filter(stop_id__in=stop_ids)
    available_routes = get_available_routes(stoptime_objs)
    stop['available_routes'] = available_routes

    return stop


def get_stop(stop_id: str) -> dict:
    try:
        stop = Stop.objects.get(stop_id=stop_id)
        stop = StopBriefSerializer(stop).data
        stop = extended_info(stop)

        stoptime_objs = StopTime.objects.filter(stop_id=stop_id)
        carrier_code = stop['carrier']['carrier_code']
        recent_trips = get_recent_trips(carrier_code, stoptime_objs)

        return {
            'stop': stop,
            'recent_trips': recent_trips
        }

    except:
        raise StopNotFoundError(f"Stop with id '{stop_id}' for '{carrier_code}' carrier wasn't found!")
    

def get_stops(**filters) -> list[dict]:
    try:
        if filters:
            stops = Stop.objects.filter(**filters)
            stops = StopBriefSerializer(stops, many=True).data
            stops = [extended_info(stop) for stop in stops]
        else:
            stops = Stop.objects.all().distinct('stop_name')
            stops = StopBriefSerializer(stops, many=True).data
    except:
        raise StopNotFoundError(**filters)

    return sorted(stops, key=lambda x: x['stop_name']) 
