from django.db import models


class Carrier(models.Model):
    carrier_name = models.CharField(max_length=64, unique=True)
    carrier_code = models.CharField(max_length=8, unique=True)

    class Meta:
        db_table = 'Tasker_Carriers'

class CalendarDate(models.Model):
    class ExceptionChoice(models.IntegerChoices):
        ZERO = 0
        ONE = 1

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    date = models.DateField()
    service_id = models.CharField(max_length=32)
    exception_type = models.IntegerField(choices=ExceptionChoice)

    class Meta:
        db_table ='Tasker_CalendarDates'


class Route(models.Model):
    class RouteTypeChoice(models.IntegerChoices):
        TRAM = 0
        METRO = 1
        TRAIN = 2
        BUS = 3

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    route_id = models.CharField(max_length=8, primary_key=True)
    route_short_name = models.CharField(max_length=8)
    route_long_name = models.CharField(max_length=64)
    route_type = models.IntegerField(choices=RouteTypeChoice)
    route_color = models.CharField(max_length=6)
    route_text_color =  models.CharField(max_length=6)

    class Meta:
        db_table = 'Tasker_Routes'


class Shape(models.Model):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    shape_id = models.CharField(max_length=17, primary_key=True)

    class Meta:
        db_table = 'Tasker_Shapes'
    

class ShapeSequence(models.Model):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)
    shape_pt_sequence = models.IntegerField()
    shape_pt_lat = models.DecimalField(max_digits=14, decimal_places=12)
    shape_pt_lon = models.DecimalField(max_digits=14, decimal_places=12)

    class Meta:
        db_table = 'Tasker_ShapeSequences'

    def get_location(self):
        return (self.shape_pt_lat, self.shape_pt_lon)

class Stop(models.Model):
    class LocationTypeChoice(models.IntegerChoices):
        BUS_TRAM_TRAIN_AND_USEFUL_METRO = 0
        METRO = 1
        METRO_ENTRANCE = 2
    
    class WheelChairBoardingChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    stop_id = models.CharField(max_length=10, primary_key=True)
    stop_name = models.CharField(max_length=64)
    stop_code = models.CharField(max_length=8, null=True)
    platform_code = models.CharField(max_length=8, null=True)
    stop_lat = models.FloatField()
    stop_lon = models.FloatField()
    location_type = models.IntegerField(choices=LocationTypeChoice, null=True)
    parent_station = models.CharField(max_length=8, null=True)
    wheelchair_boarding = models.IntegerField(choices=WheelChairBoardingChoice, null=True)
    stop_name_stem = models.CharField(max_length=64, null=True)
    town_name = models.CharField(max_length=32, null=True)
    street_name = models.CharField(max_length=128, null=True)

    def __str__(self):
        stop_name = Stop.objects.get(stop_id=self.parent_station).stop_name if self.parent_station else self.stop_name
        street_part = f'({self.street_name})' if self.street_name else ''
        return f'{stop_name} {self.stop_code}{street_part}'

    def get_coordinates(self):
        return (self.stop_lat, self.stop_lon)

    class Meta:
        db_table = 'Tasker_Stops'

class Trip (models.Model):
    class DirectionChoice (models.IntegerChoices):
        TUDA = 0
        SUDA = 1

    class WheelchairAccessChoice(models.IntegerChoices):
        YES = 1
        NO = 2

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    trip_id = models.CharField(max_length=32, primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    service_id = models.CharField(max_length=32)
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)
    trip_short_name = models.CharField(max_length=32, null=True)
    trip_headsign = models.CharField(max_length=128)
    direction_id = models.IntegerField(choices=DirectionChoice)
    wheelchair_accessible = models.IntegerField(choices=WheelchairAccessChoice, null=True)
    hidden_block_id = models.IntegerField(null=True, blank=True)
    brigade = models.CharField(max_length=4, null=True)
    fleet_type = models.CharField(max_length=16, null=True)

    class Meta:
        db_table = 'Tasker_Trips'
        unique_together = [['trip_id', 'route']]


class StopTime(models.Model):
    class BoardingTypeChoice (models.IntegerChoices):
        DEFAULT = 0
        ON_REQUEST = 3

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    stop_sequence = models.IntegerField()
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    arrival_time = models.CharField(max_length=8)
    departure_time = models.CharField(max_length=8)
    pickup_type = models.IntegerField(choices=BoardingTypeChoice, null=True)
    drop_off_type = models.IntegerField(choices=BoardingTypeChoice, null=True)

    class Meta:
        db_table = 'Tasker_StopTimes'
        unique_together = [['trip', 'stop_sequence']]

class Frequence(models.Model):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    start_time = models.CharField(max_length=8)
    end_time = models.CharField(max_length=8)
    headway_secs = models.IntegerField()
    exact_times = models.IntegerField()

    class Meta:
        db_table = 'Tasker_Frequencies'


class Transfer(models.Model):
    class TransferTypeChoice(models.IntegerChoices):
        ONE = 1
        
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    from_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='transfers_from')
    to_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='transfers_to')
    from_trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='transfers_from')
    to_trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='transfers_to')
    transfer_type = models.IntegerField(choices=TransferTypeChoice)

    class Meta:
        db_table = 'Tasker_Transfers'