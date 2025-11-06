import polyline

from django.utils import timezone as tz
from rest_framework import serializers

from .serializers import *
from Trips.services.models import *
from .models import *
from Stops.serializers import *
from common.models.common import *
from common.services.mongo import *

# TODO: add Warsaw bound coordinates to from/to params
class SearchedTripsSerializer(serializers.Serializer):
    from_lat = serializers.FloatField(
        required = True
    )
    
    from_lon = serializers.FloatField(
        required = True
    )

    to_lat = serializers.FloatField(
        required = True
    )
    
    to_lon = serializers.FloatField(
        required = True
    )
 
    datetime = serializers.DateTimeField(
        default = tz.localtime()
    )

    limit = serializers.IntegerField(
        min_value = 1,
        max_value = 100,
        default = 16
    )


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
