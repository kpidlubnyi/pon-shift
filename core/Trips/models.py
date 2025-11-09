from django.contrib.postgres.fields import ArrayField
from django.db import models
from common.models import Carrier, CarrierStaging

class AbstractTripStops(models.Model):
    """
    UNLOGGED Table.
    Defined by `_definition` below and created manually via SQL migration.
    """
    trip_id = models.CharField(max_length=64, primary_key=True)
    direction_id = models.IntegerField()
    route_id = models.CharField(max_length=8)
    stop_ids = ArrayField(models.CharField(max_length=16))

    @classmethod
    def _get_definition(cls, 
                        from_table='common_StopTimes', 
                        join_table='common_Trips', 
                        **where_filters) -> tuple[str, list]:
        from_clause = f'FROM "{from_table}" s'
        join_clause = f'JOIN "{join_table}" t USING (trip_id)'
        where_clause = ''
        params = list()
        
        if where_filters:
            conditions = []
            for key, value in where_filters.items():
                conditions.append(f'{key} = %s')
                params.append(value)
            where_clause = f"WHERE {' AND '.join(conditions)}"
        
        query = f"""
            SELECT
                s.trip_id,
                t.direction_id,
                t.route_id,
                array_agg(s.stop_id ORDER BY s.stop_sequence) AS stop_ids,
                t.carrier_id
            {from_clause}
            {join_clause}
            {where_clause}
            GROUP BY t.route_id, s.trip_id, t.direction_id, t.carrier_id
        """
        return query, params

    class Meta:
        abstract = True


class TripStops(AbstractTripStops):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    class Meta:
        db_table = 'trips_TripStops'
        managed = False


class TripStopsStaging(AbstractTripStops):
    carrier = models.ForeignKey(CarrierStaging, on_delete=models.CASCADE)
    _base_model = TripStops

    @classmethod
    def _get_definition(cls, **where_filters) -> tuple[str, list]:
        query, params = super()._get_definition(
            from_table='common_StopTimes_Staging',
            join_table='common_Trips_Staging',
            **where_filters
        )
        return query, params

    class Meta:
        db_table = 'trips_TripStops_Staging'
        managed = False