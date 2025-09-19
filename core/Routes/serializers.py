from collections import defaultdict

from rest_framework import serializers
from django.db.models import Count
from django.utils import timezone as tz

from Tasker.models.common import *
from Stops.serializers import TripSerializer


class RouteSerializer(serializers.ModelSerializer):
    most_common_trips = serializers.SerializerMethodField()
    
    def get_most_common_trips(self, obj):
        date= tz.now().strftime('%Y-%m-%d') + ':'
        data = Trip.objects.filter(
            trip_id__startswith=date,
            route_id=obj.route_id
        ).values(
            'shape_id', 
            'direction_id'
        ).annotate(
            c=Count('*')
        )

        direction_groups = defaultdict(list)
        trips = []

        for item in data:
            direction_groups[item['direction_id']].append(item)

        for items in direction_groups.values():
            max_count = 0
            shape = None

            for item in items:
                if item['c'] > max_count:
                    max_count = item['c']
                    shape = item['shape_id']
                
            trips.append(Trip.objects.filter(shape_id=shape)[0])

        trips = [TripSerializer(trip).data for trip in trips]
        result = {
            'stanom_na': date,
            'trips': trips
        }

        return result

    class Meta:
        model = Route
        fields = ['route_id', 'route_short_name', 'route_long_name', 'route_type', 'most_common_trips']