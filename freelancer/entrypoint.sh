#!/usr/bin/env sh
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn freelancer.wsgi:application --chdir freelancer --bind 0.0.0.0:8000
