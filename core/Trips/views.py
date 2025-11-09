from rest_framework import status
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from django.http import JsonResponse

from common.models.common import *
from common.services.otp_graphql import *
from .serializers import *
from .services.views import *


class TripInfo(APIView):
    def get(self, request, trip_id):
        trip = Trip.objects.get(trip_id=trip_id)
        trip = TripDetailsSerializer(trip).data
        return JsonResponse({'trip':trip}, status = status.HTTP_200_OK)


class SearchedTrips(APIView):
    def get(self, request):
        params = SearchedTripsSerializer(data=request.query_params)
            
        if not params.is_valid():
            raise ValidationError(params.errors)
        params = params.data
        variables = {
            "fromLocation": {
                "coordinates": {
                    "latitude": params['from_lat'],
                    "longitude": params['from_lon']
                }
            },
            "toLocation": {
                "coordinates": {
                    "latitude": params['to_lat'],
                    "longitude": params['to_lon']
                }
            },
            "dateTime": params['datetime'],
            "numTripPatterns": params['limit'],
            "via": build_via_variable(params.get('via'))
        }            
        
        service = OTPService()
        response = service.get_trips(**variables)

        trip = response['trip']
        trip['tripPatterns'] = [process_trip_pattern(t_pattern) for t_pattern in trip['tripPatterns']]
        return JsonResponse(trip, status=status.HTTP_200_OK)
