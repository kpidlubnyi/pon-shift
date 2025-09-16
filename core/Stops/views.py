
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from rest_framework import status
from django.http import JsonResponse

from Tasker.models import *
from .services.views import *
from .serializers import *


class BasicStopView:
    def get_stops(self, **filters) -> list[dict]:
        def get_extended_info(stop_id: str) -> tuple[list[str], str]:
            stop_id = intercept_bad_stop_id(stop_id)

            if stop_id == '7014M:P1':
                stop_ids = [stop_id, stop_id[:-1]+'2']
                stoptime_objs = StopTime.objects.filter(stop_id__in=stop_ids)
            else:
                stoptime_objs = StopTime.objects.filter(stop_id=stop_id)
            
            available_routes = get_available_routes(stoptime_objs)
            first_route = available_routes[0]

            try:
                if first_route in {'M1', 'M2'}:
                    return available_routes, 'metro'
                elif int(first_route) < 100:
                    return available_routes, 'tram'
                else:
                    return available_routes, 'bus'
            except:
                if first_route[0] == 'S':
                    return available_routes, 'train'
        
        try:
            stops = Stop.objects.filter(**filters)
            serializer = StopBriefSerializer if filters else StopOnlyNameSerializer
            stops = [serializer(stop).data for stop in stops]
            first_stop = stops[0]
        except:
            raise StopNotFoundError(**filters)
        
        by = 'stop_id' if any([field in filters.keys() for field in {'stop_code', 'stop_name'}]) else 'stop_name'
        stops = filter_stops(stops, by)
        
        if filters:
            for stop in stops:
                available_routes, vehicle_type = get_extended_info(stop['stop_id'])
                stop['available_routes'] = available_routes
                stop['vehicle_type'] = vehicle_type

        return stops
    

class AllStopsView(APIView, BasicStopView):
    def get(self, request):
        stops = self.get_stops()
        stops.sort(key=lambda x: x['stop_name'])
        return JsonResponse({'stops': stops})
    

class StopsView(APIView, BasicStopView):
    def get(self, request, stop_name):
        stops = self.get_stops(stop_name=stop_name)
        return JsonResponse({'stops':stops})
    


class StopView(APIView, BasicStopView):
    def get(self, request, stop_name, stop_code):
        stop = self.get_stops(stop_name=stop_name, stop_code=stop_code)
        stoptime_objs = StopTime.objects.filter(stop_id=stop[0]['stop_id'])
        recent_trips = get_recent_trips(stoptime_objs)

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
