#!/usr/bin/env bash
## 设置环境变量.
GUNICORN_CONCURRENCY=${GUNICORN_CONCURRENCY:-8}
GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-INFO}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-150}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-2048}

## 初始化静态资源.
mkdir -p ../public/assets
python manage.py collectstatic

command="gunicorn paasng.wsgi -w ${GUNICORN_CONCURRENCY} --timeout ${GUNICORN_TIMEOUT} -b [::]:8000 -k gevent --max-requests ${GUNICORN_MAX_REQUESTS} --access-logfile '-' --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" in %(L)s seconds' --log-level ${GUNICORN_LOG_LEVEL} --log-file=-"

## Run!
exec bash -c "$command"
