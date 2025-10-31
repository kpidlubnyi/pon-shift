from .abstract import *


class Carrier(AbstractCarrier):
    class Meta:
        db_table = 'Tasker_Carriers'

class CalendarDate(AbstractCalendarDate):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    class Meta:
        db_table ='Tasker_CalendarDates'


class Route(AbstractRoute):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_Routes'


class Shape(AbstractShape):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_Shapes'
    

class ShapeSequence(AbstractShapeSequence):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_ShapeSequences'


class Stop(AbstractStop):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_Stops'


class Trip (AbstractTrip):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_Trips'
        unique_together = [['trip_id', 'route']]


class StopTime(AbstractStopTime):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_StopTimes'
        unique_together = [['trip', 'stop_sequence']]


class Frequence(AbstractFrequence):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)

    class Meta:
        db_table = 'Tasker_Frequencies'


class Transfer(AbstractTransfer):        
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)
    from_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='transfers_from')
    to_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='transfers_to')
    from_trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='transfers_from')
    to_trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='transfers_to')

    class Meta:
        db_table = 'Tasker_Transfers'
