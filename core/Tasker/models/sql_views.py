from django.db import models
from django.contrib.postgres.fields import ArrayField

class RouteStopsMV(models.Model):
    """
    Django ORM model for the 'tasker_trip_stops' materialized view.

    This view stores pre-aggregated stop sequences for each trip, including:
      - `trip_id`: unique identifier of the trip
      - `direction_id`: direction of the trip
      - `route_id`: identifier of the route
      - `stop_ids`: ordered list of stop IDs for the trip
    """
    
    id = models.IntegerField(primary_key=True)
    trip_id = models.CharField(max_length=64)
    direction_id = models.IntegerField()
    route_id = models.CharField(max_length=8)
    stop_ids = ArrayField(models.CharField(max_length=16))

    class Meta:
        managed = False
        db_table = 'tasker_trip_stops'
