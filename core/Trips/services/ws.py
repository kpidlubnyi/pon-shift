from datetime import datetime, time
from typing import NamedTuple
from collections import UserDict

from django.db.models import QuerySet
from django.utils import timezone as tz


from common.models import *
from common.services.gtfs import *
from Trips.models import TripStops
from tasks.services.gtfs.models import add_carrier_prefix
from Routes.services.views import LocationPoint, calculate_simple_distance


AVERAGE_SPEED = {
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

class NestedDict(UserDict):
    def __getitem__(self, *keys):
        if len(keys) == 1 and isinstance(keys[0], tuple):
            keys = keys[0]

        data = self.data
        for i, k in enumerate(keys):
            if k in data:
                v = data[k]
                if keys[i+1:] and not hasattr(v, '__getitem__'):
                    raise ValueError(f'Not possible to get item from {v}')
                data = v
            else:
                raise KeyError(keys[:i+1])
        return data
            


def transform_rt_vehicle_data(carrier:str, data: dict) -> dict:
    def get_wkd_position(trip_id):
        nonlocal data, carrier
        
        trip_stop_ids = TripStops.objects.get(trip_id=trip_id).stop_ids
        next_stop_to_arrive = data['stop_time_updates'][0]['stop_id']
        id_of_previous_stop = trip_stop_ids.index(next_stop_to_arrive) - 1
        previous_stop = trip_stop_ids[id_of_previous_stop]

        return {'between': [
            {'stop_id': previous_stop},
            {'stop_id': next_stop_to_arrive}
        ]}
    
    #TODO:розібратись що не так
    def get_wtp_st_updates(self_location:LocationPoint, trip_id:str):
        def get_data_for_trip(
            trip_id:str
        ) -> tuple[Trip, QuerySet[StopTime], list[StopNT], list[ShapeSequenceNT]]:
        
            trip = Trip.objects.get(trip_id=trip_id)
            stop_times = StopTime.objects \
                .filter(trip_id=trip_id)

            stop_ids = TripStops.objects.get(trip_id=trip_id).stop_ids
            stops_locations = Stop.objects \
                .filter(stop_id__in=stop_ids) \
                .values_list('stop_id', 'stop_lat', 'stop_lon', named=True)

            shape_id = trip.shape.shape_id
            shape_sequence = ShapeSequence.objects \
                .filter(shape__shape_id=shape_id) \
                .order_by('shape_pt_sequence') \
                .values_list('id', 'shape_pt_sequence', 'shape_pt_lat', 'shape_pt_lon', named=True)
            
            return (trip, stop_times, stops_locations, shape_sequence) 

        def get_nearest_shape_point(
                self_location: LocationPoint, 
                shape_sequence: list[ShapeSequenceNT]
            ) -> LocationPoint:
            
            return min([
                (
                    s.id, 
                    s.shape_pt_sequence, 
                    calculate_simple_distance([self_location, (s.shape_pt_lat, s.shape_pt_lon)])
                )
                for s in shape_sequence
            ], key=lambda x: x[2])

        def find_next_stop(
            nearest_point: tuple[int, int, float], 
            shape_sequence: list[ShapeSequenceNT], 
            stops_locations: list[StopNT], 
            stop_times: QuerySet[StopTime]
        ) -> tuple[StopNT, int, int]:
            
            n = nearest_point[1]
            shape_sequence = shape_sequence[n:]
            next_stop = None 
            shape_sequence_n = None

            stop_n = 0
            while not next_stop:
                shape = shape_sequence[stop_n]
                location_point = (shape.shape_pt_lat, shape.shape_pt_lon)
                for stop in stops_locations:
                    stop_location = (stop.stop_lat, stop.stop_lon)
                    if calculate_simple_distance([location_point, stop_location], unit='m') <= 25:
                        next_stop = stop
                        stop_sequence_n = stop_times.get(stop_id=stop.stop_id).stop_sequence
                        shape_sequence_n = shape.shape_pt_sequence - n
                stop_n += 1

            if not next_stop:
                raise ValueError('Nearest stop to vehicle location not found!')
            
            return next_stop, stop_sequence_n, shape_sequence_n
        
        def get_location_points_from_shape_sequence( 
            shape_sequence: list[ShapeSequenceNT],
            from_point: int
        ) -> list[LocationPoint]:    
            nonlocal self_location
            shape_sequence = shape_sequence[:from_point]
            shape_sequence = [
                (s.shape_pt_lat, s.shape_pt_lon) 
                for s in shape_sequence
            ]
            return [self_location, *shape_sequence]

        def calculate_time_delta(
            trip: Trip,
            next_stop: StopNT, 
            location_points: list[LocationPoint]
        ) -> tz.timedelta:

            distance_to_next_stop = calculate_simple_distance(location_points, unit='m')
            vehicle_speed = AVERAGE_SPEED[trip.route.route_type] / 3.6
            mins_to_next_stop = tz.timedelta(minutes=(distance_to_next_stop / vehicle_speed) // 60) 
            
            now = tz.now()
            next_stop = stop_times.get(stop__stop_id=next_stop.stop_id)
            midnight = tz.make_aware(datetime.combine(tz.localdate(), time(0, 0)))
            next_stop_ar_time = midnight + parse_gtfs_time(next_stop.arrival_time)

            if next_stop_ar_time - now >= tz.timedelta(days=1):
                next_stop_ar_time -= tz.timedelta(days=1)

            rt_ar_time = now + mins_to_next_stop
            delta = rt_ar_time - next_stop_ar_time 
            return delta


        trip, stop_times, stop_locs, shape_seq = get_data_for_trip(trip_id)
        nearest_point = get_nearest_shape_point(self_location, shape_seq)
        next_stop, stop_seq_n, shape_seq_n = find_next_stop(
            nearest_point, shape_seq, 
            stop_locs, stop_times
        )
        location_points = get_location_points_from_shape_sequence(shape_seq, shape_seq_n)
        delta = calculate_time_delta(trip, next_stop, location_points)
        from_next_stop_to_end = stop_times.filter(stop_sequence__gte=stop_seq_n)
        
        stop_time_update = list()
        for s in from_next_stop_to_end:
            arrival_time = tz.datetime.strptime(s.arrival_time, '%H:%M:%S').time()
            arrival_time_dt = tz.datetime.combine(tz.localdate(), arrival_time)
            rt_arrival_time = (arrival_time_dt + delta).timestamp()
            
            stop_time_update.append({
                'departure': {
                    'timestamp': rt_arrival_time,
                    'time': tz.datetime.strftime(arrival_time_dt + delta, '%H:%M:%S'),
                    'delta': delta.seconds
                },
                'stop_id':s.stop_id,
                'stop_name': Stop.objects.get(stop_id=s.stop_id).stop_name
            }) 

        return stop_time_update

    try:
        data = NestedDict(data)
        new_data = dict()
        new_data['carrier'] = carrier

        match carrier:
            case 'WTP':       
                try: 
                    new_data['trip_id'] = add_carrier_prefix(carrier, data['vehicle', 'trip', 'trip_id'])
                    new_data['position'] = data['vehicle', 'position']
                    new_data['vehicle_number'] = data['vehicle', 'vehicle', 'label']

                    lat, lon = map(lambda x: float(new_data['position'][x]), ('latitude', 'longitude'))
                    new_data['stop_time_updates'] = get_wtp_st_updates((lat, lon), new_data['trip_id'])
                except Exception as e:
                    raise Exception(f'error in wtp case: {e}')
            case 'WKD':
                new_data['trip_id'] = add_carrier_prefix(carrier, data['trip_update', 'trip', 'trip_id'])
                new_data['position'] = get_wkd_position(new_data['trip_id'])
                new_data['stop_time_updates'] = data['stop_time_updates']
    except Exception as e:
        raise Exception(f'error in main body: {e}')
    return new_data
