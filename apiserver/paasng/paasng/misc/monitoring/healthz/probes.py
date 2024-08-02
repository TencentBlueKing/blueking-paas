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

from typing import List, Type, Union

from blue_krill.monitoring.probe.base import Issue, VirtualProbe
from blue_krill.monitoring.probe.http import BKHttpProbe, HttpProbe
from blue_krill.monitoring.probe.mysql import MySQLConfig, MySQLProbe, transfer_django_db_settings
from blue_krill.monitoring.probe.redis import RedisProbe, RedisSentinelProbe
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from paasng.settings.utils import is_redis_sentinel_backend
from paasng.utils.blobstore import StoreType, detect_default_blob_store


def get_default_healthz_token():
    return settings.HEALTHZ_TOKEN


def get_default_probes():
    probe_modules = settings.HEALTHZ_PROBES
    probes = []
    for probe_module in probe_modules:
        probes.append(import_string(probe_module))
    return probes


class BKConsoleProbe(MySQLProbe):
    name = "console"
    is_core = False

    def __init__(self):
        super().__init__()
        self.config = transfer_django_db_settings(settings.BK_CONSOLE_DBCONF)


# The database config might be absent when running "collectstatic" command in the
# docker building process, skip the probe config initialization in this case or it
# will raise an exception.
_empty_probe_config = MySQLConfig("", 0, "", "", "")

_default_mysql_probe_config = _empty_probe_config
if (_default_db := settings.DATABASES.get("default")) and _default_db["ENGINE"] != "django.db.backends.dummy":
    _default_mysql_probe_config = transfer_django_db_settings(_default_db)


class PlatformMysqlProbe(MySQLProbe):
    name = "platform-mysql-ng"
    config = _default_mysql_probe_config


_wl_mysql_probe_config = _empty_probe_config
if (_wl_db := settings.DATABASES.get("workloads")) and _wl_db["ENGINE"] != "django.db.backends.dummy":
    _wl_mysql_probe_config = transfer_django_db_settings(_wl_db)


class WorkloadsMysqlProbe(MySQLProbe):
    name = "platform-mysql-wl"
    config = _wl_mysql_probe_config


class ESBProbe(BKHttpProbe):
    name = "esb"
    url = settings.COMPONENT_SYSTEM_HEALTHZ_URL
    params = {"token": get_default_healthz_token()}


class APIGWProbe(BKHttpProbe):
    name = "apigw"
    url = settings.APIGW_HEALTHZ_URL
    params = {"token": get_default_healthz_token()}
    is_core = False


class BKDocsProbe(HttpProbe):
    name = "bkdocs"
    url = settings.BKDOC_URL
    is_core = False


class _RGWProbe(HttpProbe):
    name = "rgw"
    url = settings.BLOBSTORE_S3_ENDPOINT


class _BkRepoProbe(HttpProbe):
    name = "bkrepo"

    bkrepo_endpoint = ""
    if isinstance(settings.BLOBSTORE_BKREPO_CONFIG, dict):
        bkrepo_endpoint = settings.BLOBSTORE_BKREPO_CONFIG.get("ENDPOINT", "")
    url = f"{bkrepo_endpoint}/generic/actuator/info"


class BKIAMProbe(HttpProbe):
    name = "bkiam"

    iam_host = settings.BK_IAM_V3_INNER_URL
    if getattr(settings, "BK_IAM_USE_APIGATEWAY", False):
        iam_host = getattr(settings, "BK_IAM_APIGATEWAY_URL", "")
    url = f"{iam_host}/ping"
    is_core = True


class ServiceHubProbe(VirtualProbe):
    name = "bk-services"
    is_core = False

    def diagnose(self) -> List[Issue]:
        from paasng.accessories.servicehub.remote.collector import (
            FetchRemoteSvcError,
            RemoteSvcConfig,
            RemoteSvcFetcher,
        )

        try:
            remote_svc_configs = settings.SERVICE_REMOTE_ENDPOINTS
        except AttributeError:
            return [
                Issue(
                    fatal=True,
                    description="Can't initialize remote services, SERVICE_REMOTE_ENDPOINTS is not configured",
                )
            ]

        issues = []
        for endpoint_conf in remote_svc_configs:
            config = RemoteSvcConfig.from_json(endpoint_conf)
            fetcher = RemoteSvcFetcher(config)
            try:
                fetcher.fetch()
            except FetchRemoteSvcError:
                issues.append(
                    Issue(
                        fatal=True,
                        description=_("远程增强服务「{config_name}」状态异常, 请检查服务可用性。").format(
                            config_name=config.name
                        ),
                    )
                )
            except Exception:
                issues.append(
                    Issue(
                        fatal=True,
                        description=_("探测远程增强服务「{config_name}」时发生未知异常, 请检查配置情况。").format(
                            config_name=config.name
                        ),
                    )
                )
        return issues


class _RedisProbe(RedisProbe):
    name = "platform-redis"
    redis_url = settings.REDIS_URL


class _RedisSentinelProbe(RedisSentinelProbe):
    name = "platform-redis"
    redis_url = settings.REDIS_URL
    master_name = settings.SENTINEL_MASTER_NAME
    sentinel_kwargs = {"password": settings.SENTINEL_PASSWORD}


def _get_redis_probe_cls() -> Union[Type[_RedisSentinelProbe], Type[_RedisProbe]]:
    if is_redis_sentinel_backend(settings.REDIS_URL):
        return _RedisSentinelProbe
    return _RedisProbe


def _get_blob_store_probe_cls() -> Union[Type[_RGWProbe], Type[_BkRepoProbe]]:
    store_type = detect_default_blob_store()
    if store_type == StoreType.S3:
        return _RGWProbe
    return _BkRepoProbe


PlatformRedisProbe = _get_redis_probe_cls()

PlatformBlobStoreProbe = _get_blob_store_probe_cls()
