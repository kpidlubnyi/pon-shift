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
                return
            trip_id = leg['serviceJourney']['id'].split(':')[1]
            trip = Trip.objects.get(trip_id=trip_id)
            trip = TripBriefSerializer(trip).data
            leg['trip'] = trip
            del leg['serviceJourney']

        def replace_authority_with_carrier():
            if not leg['authority']:
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


    
        

