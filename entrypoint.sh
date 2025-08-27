#!/bin/sh
set -e

case "$1" in
  web)
    echo "Starting Gunicorn (Django web)..."
    python manage.py migrate --noinput
    python manage.py role_seed
    exec gunicorn freelancer.wsgi:application --bind 0.0.0.0:8000 --workers 3
    ;;
    
  celery)
    echo "Starting Celery worker..."
    exec celery -A freelancer worker -l info
    ;;

  # celery-beat)
  #   echo "Starting Celery Beat..."
  #   exec celery -A freelancer beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  #   ;;

  *)
    echo "Unknown command: $1"
    echo "Usage: entrypoint.sh {web|celery|celery-beat}"
    exit 1
    ;;
esac
