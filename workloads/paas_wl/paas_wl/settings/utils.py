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
import os
import socket
from typing import Dict, List, Optional, Tuple, Union

from blue_krill.secure.dj_environ import SecureEnv
from dynaconf.base import LazySettings


def get_database_conf(
    settings: LazySettings, encrypted_url_var: str = 'DATABASE_URL', env_var_prefix: str = '', for_tests: bool = False
) -> Optional[Dict]:
    """Get a database config dict, will try to read encrypted database url first

    :param encrypted_url_var: The name which stores encrypted database url
    :param env_var_prefix: The prefix string for reading all database config keys
    :param for_tests: Whether the conf will be used for running unittests, if True,
        the database name will be prepend with a `"test_"` prefix.
    """
    # 兼容逻辑：允许通过单个环境变量设置数据库连接串（需加密）
    if encrypted_url_var in os.environ:
        return SecureEnv().db_url(encrypted_url_var)

    DATABASE_NAME = settings.get(env_var_prefix + "DATABASE_NAME")
    if DATABASE_NAME:
        DATABASE_USER = settings.get(env_var_prefix + "DATABASE_USER", None)
        DATABASE_PASSWORD = settings.get(env_var_prefix + "DATABASE_PASSWORD", None)
        DATABASE_HOST = settings.get(env_var_prefix + "DATABASE_HOST", None)
        DATABASE_PORT = settings.get(env_var_prefix + "DATABASE_PORT", None)
        DATABASE_OPTIONS = settings.get(env_var_prefix + "DATABASE_OPTIONS", {})

        result = {
            "ENGINE": 'django.db.backends.mysql',
            "NAME": DATABASE_NAME,
            "USER": DATABASE_USER,
            "PASSWORD": DATABASE_PASSWORD,
            "HOST": DATABASE_HOST,
            "PORT": DATABASE_PORT,
            "OPTIONS": DATABASE_OPTIONS,
        }
        # Use a test database name when running tests to avoid unexpected changes
        if for_tests:
            result['NAME'] = f"test_{result['NAME']}"
        return result
    return None


NAME_FOR_SIMPLE_JWT = 'ONE_SIMPLE_JWT_AUTH_KEY'


def get_internal_services_jwt_auth_conf(settings: LazySettings) -> Optional[Dict]:
    """Get INTERNAL_SERVICES_JWT_AUTH_CONF from LazySettings object"""
    result = settings.get('INTERNAL_SERVICES_JWT_AUTH_CONF')
    if result:
        return result

    key = settings.get(NAME_FOR_SIMPLE_JWT)
    if key:
        return {'iss': 'paas-v3', 'key': key}
    return None


def get_paas_service_jwt_clients(settings: LazySettings) -> List:
    """Get PAAS_SERVICE_JWT_CLIENTS from LazySettings object"""
    jwt_clients = settings.get('PAAS_SERVICE_JWT_CLIENTS') or []
    key = settings.get(NAME_FOR_SIMPLE_JWT)
    if key:
        jwt_clients.append({'iss': 'paas-v3', 'key': key})
    return jwt_clients


def get_default_keepalive_options() -> Optional[Dict]:
    """Mac OS's socket module does not has below attrs, return empty options instead"""
    try:
        return {
            socket.TCP_KEEPIDLE: 60,  # type: ignore
            socket.TCP_KEEPINTVL: 10,
            socket.TCP_KEEPCNT: 6,
        }
    except AttributeError:
        return None


def is_redis_backend(backend: Optional[Union[List, Tuple, str]]) -> bool:
    """Check if given celery broker URL is "redis" type"""
    if not backend:
        return False

    value = backend[0] if isinstance(backend, (list, tuple)) else backend
    return value.startswith('redis://') or value.startswith('sentinel://')


def is_redis_sentinel_backend(backend: Optional[Union[List, Tuple, str]]) -> bool:
    """Check if given celery backend is 'redis sentinel' type"""
    if not backend:
        return False

    value = backend[0] if isinstance(backend, (list, tuple)) else backend
    return value.startswith('sentinel://')
