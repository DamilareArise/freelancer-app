#!/bin/sh
set -e
ls -la
cd freelancer/

case "$1" in
  web)
    echo "Starting Gunicorn (Django web)..."
    python manage.py migrate --noinput
    exec gunicorn freelancer.wsgi:application --bind 0.0.0.0:8000 --workers 3
    ;;
  celery)
    echo "Starting Celery worker..."
    exec celery -A freelancer worker -l info
    ;;
  *)
    echo "Unknown command: $1"
    echo "Usage: entrypoint.sh {web|celery|celery-beat}"
    exit 1
    ;;
esac
