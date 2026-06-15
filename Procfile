release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile -
worker: celery -A config worker --loglevel=INFO
