import polyline

from rest_framework import serializers

from .services.views import *
from Stops.serializers import *
from common.models.common import *
from common.services.mongo import *


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
        stops = get_stops_for_trip_stops_mv(obj)
        return StopOnMapBriefSerializer(stops, many=True).data

    def get_polyline(self, obj:TripStops):
        stops = get_stops_for_trip_stops_mv(obj)
        coords = [(s.stop_lat, s.stop_lon) for s in stops]
        return polyline.encode(coords)
         
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
