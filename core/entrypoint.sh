#!/bin/sh
set -e

echo "Waiting for Postgres..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
done

echo "Postgres is up, running migrations..."
python manage.py makemigrations
python manage.py migrate --noinput

echo "Migrations successfully completed! Creating a GTFS updating task..."
python manage.py create_gtfs_update_checker_task -m 0

echo "Created. Creating a OSM update checker..."
python manage.py create_osm_update_checker_task -m "*/5"

echo "Created. Creating a GTFS-RT updaters..."
python manage.py create_gtfs_rt_update_tasks -m "*/1"

exec "$@"