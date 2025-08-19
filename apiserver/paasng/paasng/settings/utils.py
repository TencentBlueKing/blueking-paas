# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import os
import re
import socket
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from blue_krill.redis_tools.sentinel import SentinelBackend
from blue_krill.secure.dj_environ import SecureEnv
from dynaconf.base import LazySettings
from dynaconf.utils import object_merge
from environ import Env


def get_database_conf(
    settings: LazySettings, encrypted_url_var: str = "DATABASE_URL", env_var_prefix: str = "", for_tests: bool = False
) -> Optional[Dict]:
    """Get a database config dict, will try to read encrypted database url first

    :param encrypted_url_var: The name which stores encrypted database url
    :param env_var_prefix: The prefix string for reading all database config keys
    :param for_tests: Whether the conf will be used for running unittests, if True,
        the database name will be prepend with a "test_" prefix.
    """
    # 兼容逻辑：允许通过单个环境变量设置数据库连接串（需加密）
    if encrypted_url_var in os.environ:
        return SecureEnv().db_url(encrypted_url_var)

    database_name = settings.get(env_var_prefix + "DATABASE_NAME")
    if database_name:
        database_user = settings.get(env_var_prefix + "DATABASE_USER", None)
        database_password = settings.get(env_var_prefix + "DATABASE_PASSWORD", None)
        database_host = settings.get(env_var_prefix + "DATABASE_HOST", None)
        database_port = settings.get(env_var_prefix + "DATABASE_PORT", None)
        database_options = settings.get(env_var_prefix + "DATABASE_OPTIONS", {})

        result = {
            "ENGINE": "django.db.backends.mysql",
            "NAME": database_name,
            "USER": database_user,
            "PASSWORD": database_password,
            "HOST": database_host,
            "PORT": database_port,
            "OPTIONS": database_options,
        }
        # Use a test database name when running tests to avoid unexpected changes
        if for_tests:
            result["NAME"] = f"test_{result['NAME']}"
        return result
    return None


NAME_FOR_SIMPLE_JWT = "ONE_SIMPLE_JWT_AUTH_KEY"


def get_paas_service_jwt_clients(settings: LazySettings) -> List:
    """Get PAAS_SERVICE_JWT_CLIENTS from LazySettings object"""
    jwt_clients = settings.get("PAAS_SERVICE_JWT_CLIENTS") or []
    key = settings.get(NAME_FOR_SIMPLE_JWT)
    if key:
        jwt_clients.append({"iss": "paas-v3", "key": key})
    return jwt_clients


def get_default_keepalive_options() -> Optional[Dict]:
    """MacOS's socket module does not have below attrs, return empty options instead"""
    try:
        return {
            socket.TCP_KEEPIDLE: 60,  # type: ignore
            socket.TCP_KEEPINTVL: 10,
            socket.TCP_KEEPCNT: 6,
        }
    except AttributeError:
        return None


def get_service_remote_endpoints(settings: LazySettings) -> List[Dict]:
    """
    远程增强服务配置，支持简配的三类模板（mysql，bkrepo，rabbitmq）

    配置项：
    - SERVICE_REMOTE_ENDPOINTS 完整增强服务配置（最高优先级）
    - ONE_SIMPLE_JWT_AUTH_KEY 增强服务共用 Jwt Key（简单配置 + 模板模式必须）
    - RSVC_BUNDLE_MYSQL_ENDPOINT_URL Mysql 增强服务地址
    - RSVC_BUNDLE_BKREPO_ENDPOINT_URL BKRepo 增强服务地址
    - RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL RabbitMQ 增强服务地址
    - RSVC_BUNDLE_OTEL_ENDPOINT_URL OTEL-APM 增强服务地址
    """
    endpoints = settings.get("SERVICE_REMOTE_ENDPOINTS", [])
    if endpoints:
        return endpoints

    jwt_key = settings.get(NAME_FOR_SIMPLE_JWT)
    if not jwt_key:
        return []

    template = {
        "provision_params_tmpl": {
            "engine_app_name": "{engine_app.name}",
            "operator": "{engine_app.owner}",
        },
        "jwt_auth_conf": {
            "iss": "paas-v3",
            "key": jwt_key,
        },
        "prefer_async_delete": True,
    }

    mysql_ep_url = settings.get("RSVC_BUNDLE_MYSQL_ENDPOINT_URL")
    if mysql_ep_url:
        endpoints.append(
            object_merge(
                template,
                {
                    "name": "mysql_remote",
                    "endpoint_url": mysql_ep_url,
                    "provision_params_tmpl": {"egress_info": "{cluster_info.egress_info_json}"},
                },
            )
        )

    bkrepo_ep_url = settings.get("RSVC_BUNDLE_BKREPO_ENDPOINT_URL")
    if bkrepo_ep_url:
        endpoints.append(
            object_merge(
                template,
                {
                    "name": "svc_bk_repo",
                    "endpoint_url": bkrepo_ep_url,
                    "provision_params_tmpl": {
                        "app_developers": "{app_developers}",
                    },
                },
            )
        )

    rabbitmq_ep_url = settings.get("RSVC_BUNDLE_RABBITMQ_ENDPOINT_URL")
    if rabbitmq_ep_url:
        endpoints.append(
            object_merge(
                template,
                {
                    "name": "svc_rabbitmq",
                    "endpoint_url": rabbitmq_ep_url,
                },
            )
        )
    otel_ep_url = settings.get("RSVC_BUNDLE_OTEL_ENDPOINT_URL")
    if otel_ep_url:
        endpoints.append(
            object_merge(
                template,
                {
                    "name": "svc_otel",
                    "endpoint_url": otel_ep_url,
                    "provision_params_tmpl": {
                        "app_code": "{application.code}",
                        "tenant_id": "{application.tenant_id}",
                        "bk_monitor_space_id": "{bk_monitor_space_id}",
                        "env": "{env.environment}",
                    },
                    "is_ready": settings.get("RSVC_BUNDLE_OTEL_ENABLED", False),
                },
            )
        )
    return endpoints


def is_redis_backend(backend: Optional[Union[Tuple, List, str]]) -> bool:
    """Check if given celery backend is 'redis' type"""
    if not backend:
        return False

    value = backend[0] if isinstance(backend, (list, tuple)) else backend
    return value.startswith(("redis://", "rediss://", "sentinel://"))


def is_redis_sentinel_backend(backend: Optional[Union[Tuple, List, str]]) -> bool:
    """Check if given celery backend is 'redis sentinel' type"""
    if not backend:
        return False

    value = backend[0] if isinstance(backend, (list, tuple)) else backend
    return value.startswith("sentinel://")


def is_in_celery_worker(argv: Optional[List] = None) -> bool:
    """Check if current module is running inside the celery worker.
    An valid celery command: "celery -A paasng worker -l info"

    :param argv: The command args list, default to sys.argv.
    """
    argv = argv or sys.argv
    found_celery, found_worker = False, False
    for arg in argv:
        # The celery command might be an absolute path, use search instead of equal
        if re.search(r"\bcelery$", arg):
            found_celery = True
            continue
        if arg == "worker" and found_celery:
            found_worker = True
            break
    return found_celery and found_worker


def cache_from_redis_sentinel_url(url: str, sentinel_manager: str, sentinel_password: str) -> Dict[str, Any]:
    """Parse a redis sentinel url to django CACHES setting"""
    backend = SentinelBackend(url, sentinel_manager, {"password": sentinel_password})
    return {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{sentinel_manager}/{backend.db}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.SentinelClient",
            "SENTINELS": [[host["host"], host["port"]] for host in backend.hosts],
            # redis sentinel 密码
            "SENTINEL_KWARGS": {"password": sentinel_password},
            "CONNECTION_POOL_CLASS": "redis.sentinel.SentinelConnectionPool",
            "CONNECTION_FACTORY": "django_redis.pool.SentinelConnectionFactory",
            # redis 实例密码
            "PASSWORD": backend.password,
        },
    }


def cache_from_redis_url(url: str) -> Dict[str, Any]:
    """根据 redis url 生成 django CACHES setting

    :param url: redis url（非 sentinel 类型），如：redis://localhost:6379/0
    """
    cache_cfg = Env.cache_url_config(url)

    # django_redis 会使用 pool 初始化 redisClient，分析源码 & 文档可知，
    # 其 ssl 证书需要放在 OPTIONS.CONNECTION_POOL_KWARGS 中，因此这里做下转换
    # 参考：
    # - https://github.com/jazzband/django-redis/blob/5.4.0/README.rst#ssltls-and-self-signed-certificates
    # - https://github.com/jazzband/django-redis/blob/2a3770f1/django_redis/pool.py#L124
    # - https://github.com/redis/redis-py/blob/2c9f41f4/redis/connection.py#L1089
    # - https://github.com/redis/redis-py/blob/2c9f41f4/redis/connection.py#L1227
    # - https://github.com/redis/redis-py/blob/2c9f41f4/redis/connection.py#L1048
    # - https://github.com/redis/redis-py/blob/2c9f41f4/redis/connection.py#L820
    #
    # 注意：CACHES 暂不配置 REDIS_CONNECTION_OPTIONS，该配置目前仅用于 Redis 作为 Celery 消息队列时

    # 当存在 ssl 相关配置时，需要挪位置到 CONNECTION_POOL_KWARGS 中
    if cache_cfg_options := cache_cfg.get("OPTIONS"):
        connection_pool_kwargs = cache_cfg_options.pop("CONNECTION_POOL_KWARGS", {})
        for key in ["ssl_ca_certs", "ssl_certfile", "ssl_keyfile", "ssl_cert_reqs", "ssl_check_hostname"]:
            if key.upper() in cache_cfg_options:
                connection_pool_kwargs[key] = cache_cfg_options.pop(key.upper())

        cache_cfg_options["CONNECTION_POOL_KWARGS"] = connection_pool_kwargs

    return cache_cfg
