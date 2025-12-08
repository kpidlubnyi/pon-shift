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
    
    def get_all_possible_routes(self, obj:Route):
        def get_main_trip_index(trips:list[dict], seps:list[str], route_l_name:str, direction:int) -> int:
            for sep in seps:
                if sep in route_l_name:
                    from_st, to_st = [st_name.strip() for st_name in route_l_name.split(sep)]
                    
                    if direction == 1:
                        from_st, to_st = to_st, from_st
                    break
            
            for i, trip in enumerate(trips):
                trip_from_st = trip['stops'][0]['stop_name'].strip()
                trip_to_st = trip['stops'][-1]['stop_name'].strip()                

                if from_st == trip_from_st and to_st == trip_to_st:
                    return i


        def get_calculated_main_trip_index(trips_qs:QuerySet[TripStops]) -> int:
            nonlocal obj, direction
            main_trip_qs = (
                TripStops.objects
                            .filter(route_id=obj.route_id, direction_id=direction)
                            .annotate(count_of_uses=Count('trip_id'))
                            .order_by('-count_of_uses')
                            .first()
                        )
            main_trip_stops = main_trip_qs.stop_ids

            for i, trip in enumerate(trips_qs):
                if main_trip_stops == trip.stop_ids:
                    return i            

        result = {}

        for direction in {0, 1}:
            trips_qs = (
                TripStops.objects
                    .filter(route_id=obj.route_id, direction_id=direction)
                    .distinct('stop_ids')
            )
            trips = TripStopsSerializer(trips_qs, many=True).data
            
            route_l_name = obj.route_long_name
            seps = ['→', '–']

            if any([sep in route_l_name for sep in seps]):
                main_trip_index = get_main_trip_index(trips, seps, route_l_name, direction)
            else:
                main_trip_index = get_calculated_main_trip_index(trips_qs)
                
            main_trip = trips.pop(main_trip_index)
            other_trips = trips
            
            to_fullname = lambda x: f"{x['stop_name']} {x['stop_code']}"
            main_trip_stops = {to_fullname(stop) for stop in main_trip['stops']}
            
            for trip in other_trips:
                for i, stop in enumerate(trip['stops']):
                    stop['intersection'] = True if to_fullname(stop) in main_trip_stops else False
                    stop['position'] = 'start' if i == 0 else 'end' if i == len(trip['stops'])-1 else 'middle' 
            
            result[f'direction_{direction}'] = {
                'main_route': main_trip,
                'other_routes': other_trips 
            }

        return result
    
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
