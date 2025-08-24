#!/usr/bin/env sh
set -e

echo "Applying database migrations..."
python freelancer/manage.py migrate --noinput

echo "Collecting static files..."
python freelancer/manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn freelancer.wsgi:application --chdir freelancer --bind 0.0.0.0:8000
