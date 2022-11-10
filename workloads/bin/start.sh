#!/usr/bin/env bash
## Run!
command="gunicorn paas_wl.wsgi -w 8 --timeout 150 -b [::]:8000 -k gevent --max-requests 2048 --access-logfile '-' --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" in %(L)s seconds' --log-level INFO --log-file=-"
exec bash -c "$command"
