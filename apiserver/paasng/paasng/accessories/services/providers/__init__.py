# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, Type

from . import schemas
from .base import BaseProvider, ResourcePoolProvider
from .mysql.provider import MySQLProvider
from .rabbitmq.provider import RabbitMQProvider
from .sentry.provider import SentryProvider

provider_maps: Dict[str, Type[BaseProvider]] = {
    "mysql": MySQLProvider,
    "rabbitmq": RabbitMQProvider,
    "sentry": SentryProvider,
    "pool": ResourcePoolProvider,
}

plan_schema_maps: Dict[str, Dict] = {
    "mysql": schemas.MySQLConfigSchema.schema(),
    "rabbitmq": schemas.RabbitMQConfigSchema.schema(),
    "sentry": schemas.SentryConfigSchema.schema(),
    "pool": schemas.ResourcePoolConfigSchema.schema(),
}

instance_schema_maps: Dict[str, Dict] = {
    "mysql": schemas.MySQLInstanceSchema.schema(),
    "rabbitmq": schemas.RabbitMQInstanceSchema.schema(),
    "sentry": schemas.SentryInstanceSchema.schema(),
    "redis": schemas.RedisInstanceSchema.schema(),
}

_default_schema = {"title": "EmptySchema", "type": "object", "properties": {}}


def get_provider_cls_by_provider_name(name: str) -> Type[BaseProvider]:
    if name not in provider_maps:
        raise ValueError(f"Unsupported server<{name}>")
    return provider_maps[name]


def get_provider_choices() -> Dict[str, str]:
    return {name: cls.display_name for name, cls in provider_maps.items()}


def get_plan_schema_by_provider_name(name: str) -> Dict:
    return plan_schema_maps.get(name, _default_schema)


def get_instance_schema_by_service_name(name: str) -> Dict:
    return instance_schema_maps.get(name, _default_schema)
