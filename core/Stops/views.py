
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from rest_framework import status
from django.http import JsonResponse

from Tasker.models.common import *
from .services.views import *
from .serializers import *


class BasicStopView:
    def get_stops(self, **filters) -> list[dict]:
        def get_extended_info(stop: dict) -> tuple[list[str], str]:
            stop_id = intercept_bad_stop_id(stop['stop_id'])

            if stop_id == '7014M:P1':
                stop_ids = [stop_id, stop_id[:-1]+'2']
                stoptime_objs = StopTime.objects.filter(stop_id__in=stop_ids)
            else:
                stoptime_objs = StopTime.objects.filter(stop_id=stop_id)
            
            available_routes = get_available_routes(stoptime_objs)
            first_route = available_routes[0]

            try:
                if first_route in {'M1', 'M2'}:
                    vehicle_type = 'metro'
                elif int(first_route) < 100:
                    vehicle_type = 'tram'
                else:
                    vehicle_type = 'bus'
            except:
                if first_route[0] in 'ASZ':
                    vehicle_type = 'train'

            stop['vehicle_type'] = vehicle_type
            stop['available_routes'] = available_routes

            return stop
        
        try:
            stops = Stop.objects.filter(**filters)
            serializer = StopBriefSerializer if filters else StopOnlyNameSerializer
            stops = [serializer(stop).data for stop in stops]
            first_stop = stops[0]
        except:
            raise StopNotFoundError(**filters)
        
        by = 'stop_id' if any([field in filters.keys() for field in {'stop_code', 'stop_name'}]) else 'stop_name'
        stops = list(filter(lambda x: x[by], stops))
        
        if filters:
            for stop in stops:
                stop = get_extended_info(stop)

        return stops
    
    def get_carrier(self, model_obj):
        return model_obj.carrier.carrier_code
    

class AllStopsView(APIView, BasicStopView):
    def get(self, request):
        stops = self.get_stops()
        stops.sort(key=lambda x: x['stop_name'])
        return JsonResponse({'stops': stops})
    

class StopsView(APIView, BasicStopView):
    def get(self, request, stop_name):
        stops = self.get_stops(stop_name=stop_name)

        if len(stops) == 1:
            return StopView.get(self, request, stop_name)

        return JsonResponse({'stops':stops})
    


class StopView(APIView, BasicStopView):
    def get(self, request, stop_name, stop_code=None):
        stop = self.get_stops(stop_name=stop_name, stop_code=stop_code)[0]
        stop_id = stop['stop_id']
        stoptime_objs = StopTime.objects.filter(stop_id=stop_id)
        carrier = self.get_carrier(stoptime_objs.first())
        recent_trips = get_recent_trips(carrier, stoptime_objs)

        response = {
            'stop': stop,
            'recent_trips': recent_trips
        }

        return JsonResponse(response, status=status.HTTP_200_OK)

class NearestStops(APIView):
    def get(self, request):
        params = NearestStopsQueryParamsSerializer(data=request.query_params)
            
        if not params.is_valid():
            raise ValidationError(params.errors)        
        
        address = params['address'].value
        limit = params['limit'].value
        
        stops = Stop.objects.all()
        stop_ids = [StopBriefSerializer(stop).data['stop_id'] for stop in stops]
        stops = Stop.objects.filter(stop_id__in=stop_ids)

        nearest_stops = get_nearest_stops(address, stops, limit)
        response = {
            'nearest_stops': nearest_stops
        }
        return JsonResponse(
            response,
            status=status.HTTP_200_OK
            )
