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
