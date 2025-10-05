#!/bin/sh
set -e

cd freelancer/

case "$1" in
  web)
    echo "Starting Gunicorn (Django web)..."
    python manage.py migrate --noinput
    python manage.py charges_seed
    python manage.py superad_seed
    exec gunicorn freelancer.wsgi:application --bind 0.0.0.0:8000 --workers 3
    ;;
  celery)
    echo "Starting Celery worker..."
    exec celery -A freelancer worker -B -l info
    ;;
  *)
    echo "Unknown command: $1"
    echo "Usage: entrypoint.sh {web|celery|celery-beat}"
    exit 1
    ;;
esac
