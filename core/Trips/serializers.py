import polyline
import re

from django.utils import timezone as tz
from rest_framework import serializers

from .serializers import *
from Trips.services.models import *
from .models import *
from Stops.serializers import *
from common.models.common import *
from common.services.mongo import *


class SearchedTripsSerializer(serializers.Serializer):
    start = serializers.CharField(required=True)
    end = serializers.CharField(required = True)
    datetime = serializers.DateTimeField(default = tz.localtime())
    via = serializers.CharField(required = False)
    arrive_by = serializers.BooleanField(default=False)
    banned_routes = serializers.CharField(required=False)
    max_transfers = serializers.IntegerField(min_value=0, max_value=4, default=4)   
    limit = serializers.IntegerField(min_value=1, max_value=100, default=16)
    page_cursor = serializers.CharField(required=False)

    _street_modes = ['foot', 'bicycle']
    access_mode = serializers.ChoiceField(_street_modes, allow_blank=True, required=False)
    egress_mode = serializers.ChoiceField(_street_modes, allow_blank=True, required=False)
    direct_mode = serializers.ChoiceField(_street_modes, allow_blank=True, required=False)

    transit_modes = serializers.CharField(required=False)



    @staticmethod
    def _validate_cooordinate(coord:str) -> None:
            pattern = r'\d{1,2}\.\d{1,12}'
            if not re.match(pattern, coord):
                raise serializers.ValidationError('Incorrect coordinate!')
    
    def _validate_location_point(self, location_point: str):
        lat, lon = location_point.split(',')
        self._validate_cooordinate(lat)
        self._validate_cooordinate(lon)

    def validate_start(self, value:str) -> str:
        try:
            self._validate_location_point(value)
        except Exception as e:
            raise serializers.ValidationError(e)
        
        return value
    
    def validate_end(self, value:str) -> str:
        try:
            self._validate_location_point(value)
        except Exception as e:
            raise serializers.ValidationError(e)
        
        return value
    
    def validate_banned_routes(self, value:str) -> str:
        banned_routes = value.split(',')
        routes = Route.objects.all().values_list('route_id', flat=True)

        for banned_route in banned_routes:
            if banned_route not in routes:
                raise serializers.ValidationError(f'Route {banned_route} not in database!')
        
        return value
        
    def validate_via(self, value:str):
        def validate_minimum_wait_time(val:str) -> None:
            pattern = r'^(\d+[smhd])+$|^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$'
            
            if not re.match(pattern, val, re.IGNORECASE):
                raise serializers.ValidationError(
                    "Incorrent duration! Examples of correct ones: 10m, 1h, PT10M"
                )
        
        visit_points = [visit.split(',') for visit in value.split(';')]
        
        for visit_point in visit_points:
            if len(visit_point) != 3:
                raise serializers.ValidationError(
                    """
                    Every via visit point should have 3 values: 
                    lat, lon and duration of being there!
                    """)
            self._validate_cooordinate(visit_point[0])
            self._validate_cooordinate(visit_point[1])
            validate_minimum_wait_time(visit_point[2])

        return value
    
    def validate_transit_modes(self, value:str) -> str:
        acceptable_modes = ['bus', 'tram', 'rail', 'metro']
        for mode in value.split(','):
            if mode not in acceptable_modes:
                raise serializers.ValidationError(f'{mode}: mode not in acceptable modes!')
        
        return value

class BaseTripSerializer(serializers.ModelSerializer):
    route_name = serializers.SerializerMethodField()
    has_realtime = serializers.SerializerMethodField()

    def get_route_name(self, obj:Trip):
        return obj.route.route_long_name
    
    def get_has_realtime(self, obj:Trip):
        if get_rt_vehicle_data(obj.carrier.carrier_code, obj.trip_id):
            return True
        return False


    class Meta:
        model = Trip
        fields = (
            'trip_id',
            'route_name',
            'trip_headsign',
            'direction_id',
            'wheelchair_accessible',
            'fleet_type',
            'has_realtime'
        )

class TripStopsSerializer(serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()
    polyline = serializers.SerializerMethodField()

    def get_stops(self, obj):
        stops = get_stops_for_trip_stops(obj)
        return StopOnMapBriefSerializer(stops, many=True).data

    def get_polyline(self, obj:TripStops):
        trip = Trip.objects.get(trip_id=obj.trip_id)
        carrier_id = trip.carrier.pk
        shape_id = trip.shape.shape_id
        
        shape_sequence_objs = (
            ShapeSequence.objects
                .filter(
                    shape_id=shape_id,
                    carrier_id=carrier_id
                )
        )
        
        shape_sequence = [(s_obj.shape_pt_lat, s_obj.shape_pt_lon) for s_obj in shape_sequence_objs]
        return polyline.encode(shape_sequence)
         
    class Meta:
        model = TripStops
        fields = [
            'trip_id',
            'polyline',
            'stops',
        ]


class TripBriefSerializer(BaseTripSerializer, serializers.ModelSerializer):
    class Meta(BaseTripSerializer.Meta):
        pass
        

class TripDetailsSerializer(BaseTripSerializer, serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()

    def get_stops(self, obj:Trip):
        stop_times_obj = StopTime.objects.filter(trip_id=obj.trip_id)
        stops = [StopTimeSerializer(stop).data for stop in stop_times_obj]
        return stops
    
    class Meta(BaseTripSerializer.Meta):
        fields = (
            BaseTripSerializer.Meta.fields + (
                'stops',
            )
        )
