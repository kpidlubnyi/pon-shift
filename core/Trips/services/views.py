from django.db.models import QuerySet

from common.models.common import *
from Trips.models import TripStops
from core import *


def get_stops_for_trip_stops_mv(obj:TripStops) -> QuerySet[Stop]:
    stop_ids = obj.stop_ids
    stops = Stop.objects.filter(stop_id__in=stop_ids)
    stops_dict = {stop.stop_id: stop for stop in stops}
    ordered_stops = [stops_dict[sid] for sid in stop_ids if sid in stops_dict]
    return ordered_stops