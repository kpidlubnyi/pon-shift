from rest_framework.views import APIView
from django.http import JsonResponse
from .services.common import *


class NearestBikeStations(APIView):
    def get(self, request):

        radius = int(request.GET.get('radius', 200))
        limit = int(request.GET.get('limit', 7))

        location = (52.23583, 20.9991811)
        response = {
            'stations': find_bike_stations_nearby(location, radius, limit)
            }
        
        return JsonResponse(response, status=200)