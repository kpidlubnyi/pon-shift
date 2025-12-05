
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
        return JsonResponse({'stops': stops}, status=status.HTTP_200_OK)
    

class StopsView(APIView):
    def get(self, request, stop_name_or_id):
        try:
            stops = get_stops(stop_name=stop_name_or_id)
            assert len(stops)
            return JsonResponse({'stops':stops})
        except:
            stop = get_stop(stop_name_or_id)
            return JsonResponse(stop, status=status.HTTP_200_OK)


class NearestStopsView(APIView):
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

        return JsonResponse(response,status=status.HTTP_200_OK)
