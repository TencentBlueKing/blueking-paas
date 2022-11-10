#!/usr/bin/env bash
# Exit on error
set -e

mkdir -p /var/log/app

python manage.py createcachetable
python manage.py migrate


if [ "${EDITION}" != "te" ]; then

    python manage.py loaddata data/fixtures/default.json

    if [ "${RABBITMQ_DEFAULT_CLUSTER}" != "" ]; then
        python manage.py register_cluster \
        --name "${RABBITMQ_DEFAULT_CLUSTER}" \
        --host "${RABBITMQ_DEFAULT_CLUSTER_HOST}" \
        --port "${RABBITMQ_DEFAULT_CLUSTER_AMQP_PORT:-5672}" \
        --api-port "${RABBITMQ_DEFAULT_CLUSTER_API_PORT:-15672}" \
        --admin "${RABBITMQ_DEFAULT_CLUSTER_ADMIN}" \
        --password "${RABBITMQ_DEFAULT_CLUSTER_PASSWORD}" \
        --check
    fi
fi
