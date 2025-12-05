from rest_framework import serializers

from common.models.common import *


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
    def to_representation(self, instance):
        p_station = instance.parent_station
        
        if p_station:
            instance = Stop.objects.get(stop_id=p_station)

        return super().to_representation(instance)
    
    class Meta:
        model = Stop
        fields = (
            'stop_name',
            'stop_code',
            'wheelchair_boarding',
        )
    

class StopBriefSerializer(BaseStopSerializer, serializers.ModelSerializer):
    carrier = serializers.SerializerMethodField()

    def get_carrier(self, obj):
        return CarrierSerializer(obj.carrier).data
    
    class Meta(BaseStopSerializer.Meta):
        fields = BaseStopSerializer.Meta.fields + (
            'stop_id',
            'carrier'
        )


class StopOnMapBriefSerializer(BaseStopSerializer, serializers.ModelSerializer):
    class Meta(BaseStopSerializer.Meta):
        fields = BaseStopSerializer.Meta.fields + (
            'stop_lat',
            'stop_lon',
        )


class BaseStopTimeSerializer(serializers.ModelSerializer):
    on_request = serializers.SerializerMethodField()
    
    def get_on_request(self, obj):
        return True if obj.pickup_type == 3 else False  

    class Meta:
        model = StopTime
        fields = ('trip', 'arrival_time', 'on_request')


class StopTimeSerializer(BaseStopTimeSerializer):
    stop = BaseStopSerializer()
    
    class Meta(BaseStopTimeSerializer.Meta):
        fields = BaseStopTimeSerializer.Meta.fields + (
            'stop',
        )


class RecentTripStopTimeSerializer(BaseStopTimeSerializer):
    class Meta(BaseStopTimeSerializer.Meta):
        pass
