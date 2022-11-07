#!/usr/bin/env bash
## 设置环境变量
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-6}
CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
CELERY_TASK_DEFAULT_QUEUE=${CELERY_TASK_DEFAULT_QUEUE:-}

if [ "${CELERY_TASK_DEFAULT_QUEUE}" = '' ]; then
  command="celery -A paasng worker -l ${CELERY_LOG_LEVEL} --concurrency ${CELERY_CONCURRENCY}"
else
  command="celery -A paasng worker -l ${CELERY_LOG_LEVEL} --concurrency ${CELERY_CONCURRENCY} -Q ${CELERY_TASK_DEFAULT_QUEUE}"
fi

## Run!
exec bash -c "$command"
