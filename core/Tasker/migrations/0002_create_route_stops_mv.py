from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('Tasker', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE MATERIALIZED VIEW IF NOT EXISTS Tasker_trip_stops AS
                (
                SELECT
                    s.trip_id,
                    t.direction_id,
                    route_id,
                    ARRAY_AGG(stop_id ORDER BY stop_sequence) stop_ids
                FROM "Tasker_StopTimes" s
                JOIN "Tasker_Trips" t USING(trip_id)
                GROUP BY route_id, s.trip_id, t.direction_id
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_Tasker_trip_stops_trip_id
                    ON Tasker_trip_stops(trip_id);

                CREATE INDEX IF NOT EXISTS idx_Tasker_trip_stops_route_id
                    ON Tasker_trip_stops(route_id);
            """,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS Tasker_trip_stops;"
        )
    ]
