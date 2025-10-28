from collections import defaultdict

from rest_framework import serializers
from django.db.models import Count, Min
from django.utils import timezone as tz

from Tasker.models import *
from Stops.serializers import StopOnlyNameSerializer


class RouteStopsMVSerializer(serializers.ModelSerializer):
    stops = serializers.SerializerMethodField()

    def get_stops(self, obj):
        stop_ids = obj.stop_ids
        stops = Stop.objects.filter(stop_id__in=stop_ids)
        stops_dict = {stop.stop_id: stop for stop in stops}
        ordered_stops = [stops_dict[sid] for sid in stop_ids if sid in stops_dict]
        return StopOnlyNameSerializer(ordered_stops, many=True).data

    class Meta:
        model = RouteStopsMV
        fields = [
            'trip_id',
            'stops'
        ]

class BaseRouteSerializer(serializers.ModelSerializer):
    route_type = serializers.CharField(source='get_route_type_display')
    
    class Meta:
        model = Route
        fields = (
            'route_id',
            'route_type'
        )


class RouteDetailsSerializer(BaseRouteSerializer, serializers.ModelSerializer):
    all_possible_routes = serializers.SerializerMethodField()
    
    def get_all_possible_routes(self, obj: Route):
        routes = {}

        for drctn in {0, 1}:
            routes_qs = RouteStopsMV.objects.filter(route_id=obj.route_id, direction_id=drctn)
            
            main_route_qs = (routes_qs
                .annotate(count_of_uses=Count('id'))
                .order_by('-count_of_uses')
                .first()
            )

            other_routes_qs = (routes_qs
                .distinct('stop_ids')
                .exclude(stop_ids=main_route_qs.stop_ids)
            ) 
            main_route = RouteStopsMVSerializer(main_route_qs).data
            other_routes = RouteStopsMVSerializer(other_routes_qs, many=True).data
            
            
            main_route_stops = set()
            to_fullname = lambda x: f"{x['stop_name']} {x['stop_code']}"
            for stop in main_route['stops']:
                main_route_stops.add(to_fullname(stop))

            for route in other_routes:
                for i, stop in enumerate(route['stops']):
                    stop['intersection'] = True if to_fullname(stop) in main_route_stops else False
                    stop['position'] = 'start' if i == 0 else 'end' if i == len(route['stops'])-1 else 'middle' 
            
            routes[f'direction_{drctn}'] = {
                'main_route': main_route,
                'other_routes': other_routes 
            }

        return routes
    
    class Meta(BaseRouteSerializer.Meta):
        fields = BaseRouteSerializer.Meta.fields + (
            'route_short_name', 
            'route_long_name', 
            'all_possible_routes',
        )


class RouteBriefSerializer(BaseRouteSerializer, serializers.ModelSerializer):
    class Meta(BaseRouteSerializer.Meta):
        pass
