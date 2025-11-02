from django.db import models

from .common import *


class CarrierStaging(AbstractCarrier):
    _base_model = Carrier

    class Meta:
        db_table = 'common_Carriers_Staging'


class CalendarDateStaging(AbstractCalendarDate):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)

    _base_model = CalendarDate

    class Meta:
        db_table ='common_CalendarDates_Staging'


class RouteStaging(AbstractRoute):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)

    _base_model = Route

    class Meta:
        db_table = 'common_Routes_Staging'


class ShapeStaging(AbstractShape):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)

    _base_model = Shape

    class Meta:
        db_table = 'common_Shapes_Staging'
    

class ShapeSequenceStaging(AbstractShapeSequence):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    shape = models.ForeignKey(ShapeStaging, on_delete=models.CASCADE)

    _base_model = ShapeSequence

    class Meta:
        db_table = 'common_ShapeSequences_Staging'


class StopStaging(AbstractStop):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)

    _base_model = Stop

    class Meta:
        db_table = 'common_Stops_Staging'

class TripStaging(AbstractTrip):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    route = models.ForeignKey(RouteStaging, on_delete=models.CASCADE)
    shape = models.ForeignKey(ShapeStaging, on_delete=models.CASCADE)

    _base_model = Trip

    class Meta:
        db_table = 'common_Trips_Staging'
        unique_together = [['trip_id', 'route']]


class StopTimeStaging(AbstractStopTime):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE)
    stop = models.ForeignKey(StopStaging, on_delete=models.CASCADE)

    _base_model = StopTime

    class Meta:
        db_table = 'common_StopTimes_Staging'
        unique_together = [['trip', 'stop_sequence']]

class FrequenceStaging(AbstractFrequence):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE)

    _base_model = Frequence

    class Meta:
        db_table = 'common_Frequencies_Staging'

class TransferStaging(AbstractTransfer):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    from_stop = models.ForeignKey(StopStaging, on_delete=models.CASCADE, related_name='transfers_staging_from')
    to_stop = models.ForeignKey(StopStaging, on_delete=models.CASCADE, related_name='transfers_staging_to')
    from_trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE, related_name='transfers_staging_from')
    to_trip = models.ForeignKey(TripStaging, on_delete=models.CASCADE, related_name='transfers_staging_to')

    _base_model = Transfer
    
    class Meta:
        db_table = 'common_Transfers_Staging'
