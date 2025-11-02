from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse, HttpResponse

from common.models.common import *
from .serializers import *
from .services.views import *


class RouteInfo(APIView):
    def get(self, request, route_id):
        response = get_route(route_id)
        return JsonResponse(response, status=status.HTTP_200_OK)

class ShowRoute(APIView):
    def get(self, request, trip_id):
        shape_id = Trip.objects.get(trip_id=trip_id).shape.shape_id
        shape_sequence = ShapeSequence.objects.filter(shape_id=shape_id)
        route_sequence = [point.get_location() for point in shape_sequence]
        map_html = show_route(route_sequence)

        return HttpResponse(map_html, status=200)
    
