from common.models.common import *
from Routes.serializers import *
from Trips.serializers import *


def process_trip_pattern(trip_response: dict):
    def process_leg(leg: dict):
        def remove_extra_time_fields():
            nonlocal leg
            time_to_remove = 'aimed' if leg['realtime'] else 'expected'
            del leg[f'{time_to_remove}StartTime']
            del leg[f'{time_to_remove}EndTime']

            
        def add_stop_code(mode: str):
            nonlocal leg
            quay = leg[f'{mode}Place']['quay']
            if quay is None:
                return
            stop_id = quay['id'].split(':')[1]
            try:
                stop_code = Stop.objects.get(stop_id=stop_id).stop_code
            except:
                raise ValueError(f'{stop_id}')

            leg[f'{mode}Place']['quay']['stopCode'] = stop_code

        def replace_service_journey_with_trip():
            nonlocal leg
            if not leg['serviceJourney']:
                del leg['serviceJourney']
                return
            trip_id: str = leg['serviceJourney']['id']
            trip = Trip.objects.get(trip_id=trip_id)
            trip = TripBriefSerializer(trip).data
            leg['trip'] = trip
            del leg['serviceJourney']

        def replace_authority_with_carrier():
            if not leg['authority']:
                del leg['authority']
                return
            carrier_code = leg['authority']['id'].split(':')[0]
            carrier = Carrier.objects.get(carrier_code=carrier_code)
            carrier = CarrierSerializer(carrier).data
            leg['carrier'] = carrier
            del leg['authority']
            
        remove_extra_time_fields()
        add_stop_code('from')
        add_stop_code('to')
        replace_service_journey_with_trip()
        replace_authority_with_carrier()
        return leg
    
    trip_response['legs'] = [process_leg(leg) for leg in trip_response['legs']]
    return trip_response


def build_location_variable(param: str):
    lat, lon = map(float, param.split(','))
    return {"coordinates": {"latitude": lat, "longitude": lon}}
 
 
def build_via_variable(via_str: str | None) -> list | None:
    if not via_str:
        return
    
    via = list()
    for visit_point in via_str.split(';'):
        lat, lon, duration = visit_point.split(',')
        visit_json = {
            "visit": {
                "minimumWaitTime": duration,
                "coordinate": {
                   "latitude": float(lat),
                    "longitude": float(lon)
                }}}
        via.append(visit_json)
    
    return via


def get_necessary_params(params:dict, needed_params:tuple[str]) -> dict:
    return {
        param: params.get(param)
        for param in needed_params
    }


def no_needed_params(params:dict) -> bool:
    return all((1 if not v else 0 for v in params.values()))


def build_banned_variable(params:dict) -> dict | None:
    variable = dict()
    needed_params = ('lines',)
    params = get_necessary_params(params, needed_params)

    if no_needed_params(params):
        return None

    banned_routes = params.get('banned_routes') 
    if banned_routes:
        variable['lines'] = [line for line in banned_routes.split(',')]

    return variable


def build_modes_variable(params:dict) -> dict | None:
    def build_transport_modes(param):
        modes = param.split(',')
        return [{'transportMode': mode} for mode in modes]
    
    variable = dict()
    needed_params = ('access_mode', 'egress_mode', 'direct_mode', 'transit_modes')
    params = get_necessary_params(params, needed_params)

    if no_needed_params(params):
        return None
    
    access, egress, direct, transit = params.values() 

    if transit and not (access and egress):
        raise ValueError('Transit modes always goes with access and egress modes!')
    elif (bool(access) ^ bool(egress)):
        raise ValueError('Access mode always goes with egress vice versa!')
    
    if access and egress:
        variable = {
            'accessMode': access,
            'egressMode': egress
        }
        if transit:
            transit = build_transport_modes(transit)
            variable['transportModes'] = transit
    
    if direct:
        variable['directMode'] = direct

    return variable
