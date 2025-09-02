from rest_framework.views import APIView
from django.http import JsonResponse

from Tasker.models import *
from .services.views import *

class NearestStops(APIView):
    def get(self, request):
        address = request.GET.get('address')
        limit = int(request.GET.get('limit', 3))

        nearest_stops = get_n_nearest_stops(address, limit)
        return JsonResponse(nearest_stops, status=404)
    