#!/bin/sh
echo "Waiting for postgres..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Postgres is up, running migrations..."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"