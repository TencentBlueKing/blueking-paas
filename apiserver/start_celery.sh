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

## 设置环境变量
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-6}
CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
CELERY_TASK_DEFAULT_QUEUE=${CELERY_TASK_DEFAULT_QUEUE:-}

# I18N: compile .po file to .mo files
python manage.py compilemessages

if [ "${CELERY_TASK_DEFAULT_QUEUE}" = '' ]; then
  command="celery -A paasng worker -l ${CELERY_LOG_LEVEL} --concurrency ${CELERY_CONCURRENCY}"
else
  command="celery -A paasng worker -l ${CELERY_LOG_LEVEL} --concurrency ${CELERY_CONCURRENCY} -Q ${CELERY_TASK_DEFAULT_QUEUE}"
fi

## Run!
exec bash -c "$command"
