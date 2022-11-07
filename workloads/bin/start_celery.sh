#!/usr/bin/env bash
## Run!
if [[ -v CELERY_TASK_DEFAULT_QUEUE ]];
then
  command="celery -A paas_wl worker -l info --concurrency 6 -Q ${CELERY_TASK_DEFAULT_QUEUE}"
else
  command="celery -A paas_wl worker -l info --concurrency 6"
fi

exec bash -c "$command"
