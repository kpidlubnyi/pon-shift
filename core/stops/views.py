
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from rest_framework import status
from django.http import JsonResponse

from common.models.common import *
from .services.views import *
from .serializers import *


class AllStopsView(APIView):
    def get(self, request):
        stops = get_stops()
        return JsonResponse({'stops': stops})
    

class StopsView(APIView):
    def get(self, request, stop_name):
        stops = get_stops(stop_name=stop_name)

        if len(stops) == 1:
            return StopView.get(self, request, stop_name)

        return JsonResponse({'stops':stops})
    

class StopView(APIView):
    def get(self, request, stop_name, stop_code=None):
        stop = get_stops(stop_name=stop_name, stop_code=stop_code)[0]
        stop_id = stop['stop_id']
        stoptime_objs = StopTime.objects.filter(stop_id=stop_id)
        carrier_code = stop['carrier']['carrier_code']
        recent_trips = get_recent_trips(carrier_code, stoptime_objs)

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
        stop_ids = [stop.stop_id for stop in stops]
        stops = Stop.objects.filter(stop_id__in=stop_ids)

        nearest_stops = get_nearest_stops(address, stops, limit)
        response = {
            'nearest_stops': nearest_stops
        }
        return JsonResponse(
            response,
            status=status.HTTP_200_OK
            )
