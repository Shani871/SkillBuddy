#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python scripts/create_superuser.py

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile -
