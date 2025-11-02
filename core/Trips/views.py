from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse

from common.models.common import *
from .serializers import *
from .services.views import *


class TripInfo(APIView):
    def get(self, request, trip_id):
        trip = Trip.objects.get(trip_id=trip_id)
        trip = TripDetailsSerializer(trip).data
        return JsonResponse({'trip':trip}, status = status.HTTP_200_OK)
