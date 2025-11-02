from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models.common import Carrier

class TripStops(models.Model):
    """
    UNLOGGED Table.
    Defined by `_definition` below and created manually via SQL migration.
    """

    trip_id = models.CharField(max_length=64, primary_key=True)
    direction_id = models.IntegerField()
    route_id = models.CharField(max_length=8)
    stop_ids = ArrayField(models.CharField(max_length=16))
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE)

    @staticmethod
    def _get_definition(**where_filters) -> tuple[str, list]:
        where_clause = ""
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
            FROM "common_StopTimes" s
            JOIN "common_Trips" t USING (trip_id)
            {where_clause}
            GROUP BY t.route_id, s.trip_id, t.direction_id, t.carrier_id
        """

        return query, params
    
    class Meta:
        db_table = "common_TripStops"
        managed = False
        verbose_name = "Trip stops (UNLOGGED)"
