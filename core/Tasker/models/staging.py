from django.db import models

from .common import *

class CarrierStaging(models.Model):
    carrier_name = models.CharField(max_length=64, unique=True)
    carrier_code = models.CharField(max_length=8, unique=True)

    _base_model = Carrier

    class Meta:
        db_table = 'Tasker_Carriers_Staging'


class CalendarDateStaging(models.Model):
    class ExceptionChoice(models.IntegerChoices):
        ZERO = 0
        ONE = 1

    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    date = models.DateField()
    service_id = models.CharField(max_length=32)
    exception_type = models.IntegerField(choices=ExceptionChoice)

    _base_model = CalendarDate

    class Meta:
        db_table ='Tasker_CalendarDates_Staging'


class RouteStaging(models.Model):
    class RouteTypeChoice(models.IntegerChoices):
        TRAM = 0
        METRO = 1
        TRAIN = 2
        BUS = 3

    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    route_id = models.CharField(max_length=8, primary_key=True)
    route_short_name = models.CharField(max_length=8)
    route_long_name = models.CharField(max_length=64)
    route_type = models.IntegerField(choices=RouteTypeChoice)
    route_color = models.CharField(max_length=6)
    route_text_color =  models.CharField(max_length=6)

    _base_model = Route

    class Meta:
        db_table = 'Tasker_Routes_Staging'


class ShapeStaging(models.Model):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    shape_id = models.CharField(max_length=17, primary_key=True)

    _base_model = Shape

    class Meta:
        db_table = 'Tasker_Shapes_Staging'
    

class ShapeSequenceStaging(models.Model):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    shape = models.ForeignKey(ShapeStaging, on_delete=models.CASCADE)
    shape_pt_sequence = models.IntegerField()
    shape_pt_lat = models.DecimalField(max_digits=14, decimal_places=12)
    shape_pt_lon = models.DecimalField(max_digits=14, decimal_places=12)

    _base_model = ShapeSequence

    class Meta:
        db_table = 'Tasker_ShapeSequences_Staging'

    def get_location(self):
        return (self.shape_pt_lat, self.shape_pt_lon)

class StopStaging(models.Model):
    class LocationTypeChoice(models.IntegerChoices):
        BUS_TRAM_TRAIN_AND_USEFUL_METRO = 0
        METRO = 1
        METRO_ENTRANCE = 2
    
    class WheelChairBoardingChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    stop_id = models.CharField(max_length=10, primary_key=True)
    stop_name = models.CharField(max_length=32)
    stop_code = models.CharField(max_length=8, null=True)
    platform_code = models.CharField(max_length=8, null=True)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    location_type = models.IntegerField(choices=LocationTypeChoice, null=True)
    parent_station = models.CharField(max_length=8, null=True)
    wheelchair_boarding = models.IntegerField(choices=WheelChairBoardingChoice)
    stop_name_stem = models.CharField(max_length=32, null=True)
    town_name = models.CharField(max_length=32, null=True)
    street_name = models.CharField(max_length=32, null=True)

    _base_model = Stop

    def __str__(self):
        stop_name = StopStaging.objects.get(stop_id=self.parent_station).stop_name if self.parent_station else self.stop_name
        street_part = f'({self.street_name})' if self.street_name else ''
        return f'{stop_name} {self.stop_code}{street_part}'

    def get_coordinates(self):
        return (self.stop_lat, self.stop_lon)

    class Meta:
        db_table = 'Tasker_Stops_Staging'

class TripStaging(models.Model):
    class DirectionChoice (models.IntegerChoices):
        TUDA = 0
        SUDA = 1

    class WheelchairAccessChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    trip_id = models.CharField(max_length=32, primary_key=True)
    route = models.ForeignKey(RouteStaging, on_delete=models.CASCADE)
    service_id = models.CharField(max_length=32)
    shape = models.ForeignKey(ShapeStaging, on_delete=models.CASCADE)
    trip_short_name = models.CharField(max_length=32, null=True)
    trip_headsign = models.CharField(max_length=32)
    direction_id = models.IntegerField(choices=DirectionChoice)
    wheelchair_accessible = models.IntegerField(choices=WheelchairAccessChoice)
    hidden_block_id = models.IntegerField(null=True, blank=True)
    brigade = models.CharField(max_length=4, null=True)
    fleet_type = models.CharField(max_length=16, null=True)

    _base_model = Trip

    class Meta:
        db_table = 'Tasker_Trips_Staging'
        unique_together = [['trip_id', 'route_id']]


class StopTimeStaging(models.Model):
    class BoardingTypeChoice (models.IntegerChoices):
        DEFAULT = 0
        ON_REQUEST = 3

    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE)
    stop_sequence = models.IntegerField()
    stop = models.ForeignKey(StopStaging, on_delete=models.CASCADE)
    arrival_time = models.CharField(max_length=8)
    departure_time = models.CharField(max_length=8)
    pickup_type = models.IntegerField(choices=BoardingTypeChoice, null=True)
    drop_off_type = models.IntegerField(choices=BoardingTypeChoice, null=True)

    _base_model = StopTime

    class Meta:
        db_table = 'Tasker_StopTimes_Staging'
        unique_together = [['trip', 'stop_sequence']]

class FrequenceStaging(models.Model):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE)
    start_time = models.CharField(max_length=8)
    end_time = models.CharField(max_length=8)
    headway_secs = models.IntegerField()
    exact_times = models.IntegerField()

    _base_model = Frequence

    class Meta:
        db_table = 'Tasker_Frequencies_Staging'
