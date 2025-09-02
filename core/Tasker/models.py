from django.db import models


class CalendarDate(models.Model):
    class ExceptionChoice(models.IntegerChoices):
        ZERO = 0
        ONE = 1

    date = models.DateField()
    service_id = models.CharField(max_length=32)
    exception_type = models.IntegerField(choices=ExceptionChoice)

    class Meta:
        db_table ='Tasker_CalendarDates'


class Route(models.Model):
    class AgencyChoice(models.IntegerChoices):
        AGENCY = 0
        MKURAN = 1

    class RouteTypeChoice(models.IntegerChoices):
        METRO_AND_TRAM = 0
        BUS = 3

    route_id = models.CharField(max_length=8, primary_key=True)
    agency_id = models.IntegerField(choices=AgencyChoice)
    route_short_name = models.CharField(max_length=8)
    route_long_name = models.CharField(max_length=64)
    route_type = models.IntegerField(choices=RouteTypeChoice)
    route_color = models.CharField(max_length=6)
    route_text_color =  models.CharField(max_length=6)

    class Meta:
        db_table = 'Tasker_Routes'


class Shape(models.Model):
    shape_id = models.CharField(max_length=17, primary_key=True)

    class Meta:
        db_table = 'Tasker_Shapes'
    

class ShapeSequence(models.Model):
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)
    shape_pt_sequence = models.IntegerField()
    shape_pt_lat = models.DecimalField(max_digits=14, decimal_places=12)
    shape_pt_lon = models.DecimalField(max_digits=14, decimal_places=12)

    class Meta:
        db_table = 'Tasker_ShapeSequences'

class Stop(models.Model):
    class LocationTypeChoice(models.IntegerChoices):
        BUS = 0
        METRO = 2
    
    class WheelChairBoardingChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    stop_id = models.CharField(max_length=10, primary_key=True)
    stop_name = models.CharField(max_length=32)
    stop_code = models.CharField(max_length=8, null=True)
    platform_code = models.CharField(max_length=8, null=True)
    stop_lat = models.DecimalField(max_digits=8, decimal_places=6)
    stop_lon = models.DecimalField(max_digits=8, decimal_places=6)
    location_type = models.IntegerField(choices=LocationTypeChoice)
    parent_station = models.CharField(max_length=8, null=True)
    wheelchair_boarding = models.IntegerField(choices=WheelChairBoardingChoice)
    stop_name_stem = models.CharField(max_length=32, null=True)
    town_name = models.CharField(max_length=32, null=True)
    street_name = models.CharField(max_length=32, null=True)

    class Meta:
        db_table = 'Tasker_Stops'

class Trip (models.Model):
    class DirectionChoice (models.IntegerChoices):
        TUDA = 0
        SUDA = 1

    class WheelchairAccessChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    trip_id = models.CharField(max_length=32, primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    service_id = models.CharField(max_length=32)
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)
    trip_short_name = models.CharField(max_length=32, null=True)
    trip_headsign = models.CharField(max_length=32)
    direction_id = models.IntegerField(choices=DirectionChoice)
    wheelchair_accessible = models.IntegerField(choices=WheelchairAccessChoice)
    hidden_block_id = models.IntegerField(null=True, blank=True)
    brigade = models.CharField(max_length=4)
    fleet_type = models.CharField(max_length=16)

    class Meta:
        db_table = 'Tasker_Trips'
        unique_together = [['trip_id', 'route_id']]


class StopTime(models.Model):
    class BoardingTypeChoice (models.IntegerChoices):
        ZWYKLY = 0
        NA_ZADANIE = 3

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    stop_sequence = models.IntegerField()
    arrival_time = models.CharField(max_length=8)
    departure_time = models.CharField(max_length=8)
    pickup_type = models.IntegerField(choices=BoardingTypeChoice)
    drop_off_type = models.IntegerField(choices=BoardingTypeChoice)

    class Meta:
        db_table = 'Tasker_StopTimes'
        unique_together = [['trip', 'stop_sequence']]

class Frequence(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    start_time = models.CharField(max_length=8)
    end_time = models.CharField(max_length=8)
    headway_secs = models.IntegerField()
    exact_times = models.IntegerField()

    class Meta:
        db_table = 'Tasker_Frequencies'
