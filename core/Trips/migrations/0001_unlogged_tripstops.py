from django.db import migrations

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE UNLOGGED TABLE IF NOT EXISTS "common_TripStops" (
                    trip_id VARCHAR(64) PRIMARY KEY,
                    direction_id INTEGER NOT NULL,
                    route_id VARCHAR(8) NOT NULL,
                    stop_ids VARCHAR(16)[] NOT NULL,
                    carrier_id INTEGER NOT NULL REFERENCES "common_Carriers"(id)
                );

                CREATE INDEX IF NOT EXISTS common_tripstops_route_id_idx
                    ON "common_TripStops" (route_id);

                CREATE INDEX IF NOT EXISTS common_tripstops_carrier_id_idx
                    ON "common_TripStops" (carrier_id);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS "common_TripStops" CASCADE;
            """,
        ),
    ]
