from datetime import datetime
from typing import NamedTuple

from django.db.models import QuerySet
from django.utils import timezone as tz

from common.collections import NestedDict
from common.models import *
from common.services.gtfs import *
from Trips.models import TripStops
from tasks.services.gtfs.models import add_carrier_prefix
from Routes.services.views import LocationPoint, calculate_simple_distance


AVERAGE_SPEED_KM_H = {
    Route.RouteTypeChoice.TRAM: 17,
    Route.RouteTypeChoice.BUS: 25,
    Route.RouteTypeChoice.METRO: 33,
    Route.RouteTypeChoice.TRAIN: 39
}


class StopNT(NamedTuple):
    stop_id: int
    stop_lat: float
    stop_lon: float


class ShapeSequenceNT(NamedTuple):
    id: int
    shape_pt_sequence: int
    shape_pt_lat: float
    shape_pt_lon: float


def transform_rt_vehicle_data(carrier:str, data: dict) -> dict:
    def get_wkd_position(trip_id, st_updates):        
        trip_stop_ids = TripStops.objects.get(trip_id=trip_id).stop_ids
        next_stop_to_arrive = st_updates[0]['stop_id']
        prev_stop_id = trip_stop_ids.index(next_stop_to_arrive) - 1
        prev_stop = trip_stop_ids[prev_stop_id]

        return {'between': [
            {'stop_id': prev_stop},
            {'stop_id': next_stop_to_arrive}
        ]}
    
    def get_wtp_st_updates(self_location: LocationPoint, trip_id: str):        
        def get_data_for_trip(
            trip_id: str
        ) -> tuple[Trip, QuerySet[StopTime], list[StopNT], list[ShapeSequenceNT]]:
            
            trip = Trip.objects.get(trip_id=trip_id)
            stop_times = StopTime.objects.filter(trip_id=trip_id)

            stop_ids = TripStops.objects.get(trip_id=trip_id).stop_ids
            stops_locs = list(Stop.objects
                .filter(stop_id__in=stop_ids)
                .values_list('stop_id', 'stop_lat', 'stop_lon', named=True))
            
            shape_seq = list(ShapeSequence.objects 
                .filter(shape__shape_id=trip.shape.shape_id) 
                .order_by('shape_pt_sequence') 
                .values_list('id', 'shape_pt_sequence', 'shape_pt_lat', 'shape_pt_lon', named=True))
            
            return (trip, stop_times, stops_locs, shape_seq)
        
        def get_nearest_shape_p_nr(self_loc: LocationPoint, shape_seq: list[ShapeSequenceNT]) -> int:            
            shape_seq_locs = [(sh.shape_pt_lat, sh.shape_pt_lon) for sh in shape_seq]
            distances = [calculate_simple_distance([self_loc, loc], unit='m') for loc in shape_seq_locs]            
            nearest_idx = min(range(len(distances)), key=lambda x: distances[x])
            
            return nearest_idx
        
        def find_next_stop_and_its_nearest_point(shape_seq: list[ShapeSequenceNT], stops_locs: list[StopNT]):            
            for i, sh in enumerate(shape_seq):
                sh_loc = (sh.shape_pt_lat, sh.shape_pt_lon)
                
                for s in stops_locs:
                    stop_loc = (s.stop_lat, s.stop_lon)
                    distance = calculate_simple_distance([sh_loc, stop_loc], unit='m')
                    
                    if distance <= 25:
                        return s, i
            
            raise ValueError("No next stop found in 25m of shape sequence")
        
        trip, stop_times, stops_location, shape_sequence = get_data_for_trip(trip_id)
        nearest_shape_point = get_nearest_shape_p_nr(self_location, shape_sequence)
        shape_sequence = shape_sequence[nearest_shape_point:]
        
        next_stop, its_nearest_point = find_next_stop_and_its_nearest_point(shape_sequence, stops_location)
        next_stop_sequence_nr = stop_times.get(stop_id=next_stop.stop_id).stop_sequence
        stop_times = stop_times.filter(stop_sequence__gte=next_stop_sequence_nr)
        shape_sequence = shape_sequence[its_nearest_point:]
        
        next_stop_loc = (next_stop.stop_lat, next_stop.stop_lon)
        distance_to_next_stop = calculate_simple_distance([self_location, next_stop_loc])
        vehicle_speed = AVERAGE_SPEED_KM_H[trip.route.route_type] / 60.0  # km/min
        
        minutes_to_next_stop = int(distance_to_next_stop / vehicle_speed)
        delta = tz.timedelta(minutes=minutes_to_next_stop)
        
        stop_time_updates = list()
        for stop_time in stop_times.iterator():
            arrival_time = parse_gtfs_time(stop_time.arrival_time) + delta
            new_time = timedelta_to_str(arrival_time)
            stop_time_updates.append({
                "stop_id": stop_time.stop.stop_id,
                "new_time": new_time
            })
            
        return stop_time_updates   
     
    def transform_wkd_st_updates(st_updates: list[dict]):
        new_updates = list()
        for st_update in st_updates:
            st_update = NestedDict(st_update)
            stop_id = st_update['stop_id']
            
            st_time = datetime.fromtimestamp(
                int(st_update['departure.time'])
            )
            new_time = st_time.strftime('%H:%M:%S')
            
            new_updates.append({
                'stop_id': stop_id,
                'new_time': new_time
            })
        
        return new_updates
        

    data = NestedDict(data)
    new_data = dict()
    new_data['carrier'] = carrier

    match carrier:
        case 'WTP':       
            data = data['vehicle']
            new_data['trip_id'] = add_carrier_prefix(carrier, data['trip.trip_id'])
            new_data['position'] = data['position'].to_dict()
            new_data['vehicle_number'] = data['vehicle.label']

            lat, lon = map(lambda x: float(new_data['position'][x]), ('latitude', 'longitude'))
            new_data['stop_time_update'] = get_wtp_st_updates((lat, lon), new_data['trip_id'])
        case 'WKD':
            data = data['trip_update']
            new_data['trip_id'] = add_carrier_prefix(carrier, data['trip.trip_id'])
            new_data['position'] = get_wkd_position(new_data['trip_id'], data['stop_time_update'])
            new_data['vehicle_number'] = None
            new_data['stop_time_update'] = transform_wkd_st_updates(data['stop_time_update'])

    return new_data
