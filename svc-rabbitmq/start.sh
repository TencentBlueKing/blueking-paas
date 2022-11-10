#!/usr/bin/env bash
# Exit on error
set -e

mkdir -p /var/log/app

python manage.py collectstatic --no-input

## Run!
command="gunicorn svc_rabbitmq.wsgi -w 4 -b [::]:${PORT:-80} --max-requests 2048 --access-logfile '-' --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" in %(L)s seconds' --log-level INFO"
exec bash -c "$command"
