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
from blue_krill.redis_tools.sentinel import SentinelBackend
from django.conf import settings
from dogpile.cache import make_region

from paasng.settings.utils import is_redis_sentinel_backend

REDIS_URL = settings.REDIS_URL


def key_mangler(key: str):
    return "paas:v1:" + key


if is_redis_sentinel_backend(REDIS_URL):
    backend = SentinelBackend(REDIS_URL, settings.SENTINEL_MASTER_NAME, {'password': settings.SENTINEL_PASSWORD})
    region = make_region(key_mangler=key_mangler).configure(
        'dogpile.cache.redis_sentinel',
        arguments={
            'sentinels': [[host['host'], host['port']] for host in backend.hosts],
            'db': backend.db,
            'service_name': backend.master_name,
            'sentinel_kwargs': backend.sentinel_kwargs,
            'password': backend.password,
            'redis_expiration_time': 600,
            # Disable distributed lock for better performance
            'distributed_lock': False,
        },
    )
else:
    region = make_region(key_mangler=key_mangler).configure(
        'dogpile.cache.redis',
        arguments={
            'url': REDIS_URL,
            'redis_expiration_time': 600,
            # Disable distributed lock for better performance
            'distributed_lock': False,
        },
    )
