from rest_framework import serializers

from Tasker.models.common import *


class NearestStopsQueryParamsSerializer(serializers.Serializer):
    address = serializers.CharField(
        required = True
    )
    
    limit = serializers.IntegerField(
        min_value = 1,
        max_value = 10,
        default = 5
    )

    radius = serializers.FloatField(
        min_value = 0.001,
        max_value = 3,
        default = 1
    )


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = '__all__'


class BaseStopSerializer(serializers.ModelSerializer):
    carrier = serializers.SerializerMethodField()

    def to_representation(self, instance):
        p_station = instance.parent_station
        
        if p_station:
            instance = Stop.objects.get(stop_id=p_station)

        return super().to_representation(instance)
        
    def get_carrier(self, obj):
        return CarrierSerializer(obj.carrier).data
    
    class Meta:
        model = Stop
        fields = (
            'stop_name',
            'stop_code'
        )
    

class StopBriefSerializer(BaseStopSerializer, serializers.ModelSerializer):
    class Meta(BaseStopSerializer.Meta):
        fields = BaseStopSerializer.Meta.fields + (
            'stop_id',
            'wheelchair_boarding',
            'carrier'
        )


class StopOnlyNameSerializer(BaseStopSerializer, serializers.ModelSerializer):
    class Meta(BaseStopSerializer.Meta):
        pass


class StopTimeSerializer(serializers.ModelSerializer):
    stop = StopBriefSerializer()
    on_request = serializers.SerializerMethodField()
    
    def get_on_request(self, obj):
        return True if obj.pickup_type == 3 else False  

    class Meta:
        model = StopTime
        fields = ['stop', 'trip', 'arrival_time', 'on_request',]


class StopTimeBriefSerializer(StopTimeSerializer):
    class Meta:
        model = StopTime
        fields = ['stop', 'on_request']

class RecentTripStopTimeSerializer(StopTimeSerializer):
    class Meta:
        model = StopTime
        fields = ['trip', 'arrival_time', 'on_request']

class TripSerializer(serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()

    def get_stops(self, obj):
        stop_times_obj = StopTime.objects.filter(trip_id=obj.trip_id)
        stops = []

        for stop in stop_times_obj:
            stops.append(StopTimeBriefSerializer(stop).data)

        return stops
    
    class Meta:
        model = Trip
        fields = (
            'trip_id', 
            'trip_headsign', 
            'direction_id', 
            'wheelchair_accessible', 
            'stops'
        )
