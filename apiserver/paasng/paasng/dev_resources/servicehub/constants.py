# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import uuid
from enum import Enum

from blue_krill.data_types.enum import StructuredEnum

SERVICE_SENSITIVE_FIELDS = {
    'gcs_mysql': ['GCS_MYSQL_PASSWORD'],
    'mysql': ['MYSQL_PASSWORD'],
    'rabbitmq': ['RABBITMQ_PASSWORD', 'LEGACY_RABBITMQ_PASSWORD'],
}

SERVICE_HIDDEN_FIELDS = {'ceph': ['CEPH_AWS_SECRET_ACCESS_KEY']}

# 迁移服务的 plan 占位符
LEGACY_PLAN_ID = uuid.UUID('{00000000-0000-0000-0000-000000000000}')
LEGACY_PLAN_INSTANCE = dict(
    uuid=str(LEGACY_PLAN_ID),
    name="legacy-plan",
    description="迁移服务",
    is_active=True,
    is_eager=True,
    region="--",
    specifications=dict(),
    properties=dict(),
)


class Category(int, Enum):
    """Paas service categories"""

    DATA_STORAGE = 1
    MONITORING_HEALTHY = 2


class ServiceType(str, StructuredEnum):
    LOCAL = 'local'
    REMOTE = 'remote'


class ServiceBindingType(int, Enum):
    """Type of service binding relationship"""

    NORMAL = 1
    SHARING = 2
