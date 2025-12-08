from django.db import migrations

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE UNLOGGED TABLE IF NOT EXISTS "trips_TripStops" (
                    trip_id VARCHAR(64) PRIMARY KEY,
                    direction_id INTEGER NOT NULL,
                    route_id VARCHAR(8) NOT NULL,
                    stop_ids VARCHAR(16)[] NOT NULL,
                    carrier_id INTEGER NOT NULL REFERENCES "common_Carriers"(id)
                );

                CREATE INDEX IF NOT EXISTS trips_tripstops_route_id_idx
                    ON "trips_TripStops" (route_id);

                CREATE INDEX IF NOT EXISTS trips_tripstops_carrier_id_idx
                    ON "trips_TripStops" (carrier_id);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS "trips_TripStops" CASCADE;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNLOGGED TABLE IF NOT EXISTS "trips_TripStops_Staging" (
                    trip_id VARCHAR(64) PRIMARY KEY,
                    direction_id INTEGER NOT NULL,
                    route_id VARCHAR(8) NOT NULL,
                    stop_ids VARCHAR(16)[] NOT NULL,
                    carrier_id INTEGER NOT NULL REFERENCES "common_Carriers_Staging"(id)
                );

                CREATE INDEX IF NOT EXISTS trips_tripstops_staging_route_id_idx
                    ON "trips_TripStops_Staging" (route_id);

                CREATE INDEX IF NOT EXISTS trips_tripstops_staging_carrier_id_idx
                    ON "trips_TripStops_Staging" (carrier_id);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS "trips_TripStops_Staging" CASCADE;
            """,
        ),
    ]
