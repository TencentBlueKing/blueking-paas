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

python manage.py migrate --no-input
python manage.py collectstatic --no-input

# load fixtures
# python manage.py loaddata data/fixtures/services.json
# python manage.py loaddata data/fixtures/plans.json

## Run!
export prometheus_multiproc_dir="prometheus_data"

command="gunicorn svc_bk_repo.wsgi -w 4 -b [::]:5000 -k gevent --max-requests 2048 --access-logfile '-' --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" in %(L)s seconds' --log-level INFO --log-file=- --env prometheus_multiproc_dir=prometheus_data"
exec bash -c "$command"
