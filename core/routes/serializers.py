from rest_framework import serializers
from django.db.models import Count, Q, QuerySet, Min, Max
from django.utils import timezone as tz

from common.models import *
from common.services.common import *
from stops.serializers import *
from trips.models import *
from trips.serializers import *



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
    now_on_track = serializers.SerializerMethodField()
    
    def get_all_possible_routes(self, obj: Route):
        routes = {}

        for drctn in {0, 1}:
            routes_qs = TripStops.objects.filter(route_id=obj.route_id, direction_id=drctn)
            
            main_route_qs = (routes_qs
                .annotate(count_of_uses=Count('trip_id'))
                .order_by('-count_of_uses')
                .first()
            )

            other_routes_qs = (routes_qs
                .distinct('stop_ids')
                .exclude(stop_ids=main_route_qs.stop_ids)
            ) 
            main_route = TripStopsSerializer(main_route_qs).data
            other_routes = TripStopsSerializer(other_routes_qs, many=True).data
            
            
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
    
    def get_trips_for_date(self, obj: Route, date=tz.localdate(tz.now())) -> QuerySet[Trip]:
        trip_filter = Q(route_id=obj.route_id, carrier=obj.carrier)

        if obj.carrier.carrier_code == 'WTP':
            weekday_code = get_wtp_weekday(date.isoweekday())
            trip_filter &= (Q(trip_id__contains=date) & Q(trip_id__contains=weekday_code))

        trips = Trip.objects.filter(trip_filter)

        service_ids = trips.values_list('service_id', flat=True).distinct()

        calendar_dates = CalendarDate.objects.filter(
            service_id__in=service_ids,
            date=date,
        ).values('service_id', 'exception_type')

        working_services = {
            c['service_id'] for c in calendar_dates if c['exception_type'] == 1
        }
        excluded_services = {
            c['service_id'] for c in calendar_dates if c['exception_type'] == 2
        }

        return (
            trips
                .filter(service_id__in=working_services)
                .exclude(service_id__in=excluded_services)
        )

    def get_now_on_track(self, obj: Route):
        now = tz.localtime(tz.now()).time()
        trips = self.get_trips_for_date(obj)

        trips_active_now = (StopTime.objects
            .filter(trip_id__in=trips.values_list('trip_id',flat=True))
            .values('trip_id')
            .annotate(
                min_time=Min('arrival_time'),
                max_time=Max('departure_time'))
            .filter(
                min_time__lt=now,
                max_time__gt=now)
            .values_list('trip_id', flat=True)
        )

        trips = trips.filter(trip_id__in=trips_active_now)
        return TripBriefSerializer(trips, many=True).data
        
    class Meta(BaseRouteSerializer.Meta):
        fields = BaseRouteSerializer.Meta.fields + (
            'route_short_name', 
            'route_long_name', 
            'all_possible_routes',
            'now_on_track',
        )


class RouteBriefSerializer(BaseRouteSerializer, serializers.ModelSerializer):
    class Meta(BaseRouteSerializer.Meta):
        pass
