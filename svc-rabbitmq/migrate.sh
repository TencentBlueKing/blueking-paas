#!/usr/bin/env bash
##
## TencentBlueKing is pleased to support the open source community by making
## 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
## Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
## Licensed under the MIT License (the "License"); you may not use this file except
## in compliance with the License. You may obtain a copy of the License at
##
##     http://opensource.org/licenses/MIT
##
## Unless required by applicable law or agreed to in writing, software distributed under
## the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
## either express or implied. See the License for the specific language governing permissions and
## limitations under the License.
##
## We undertake not to change the open source license (MIT license) applicable
## to the current version of the project delivered to anyone in the future.
##

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
