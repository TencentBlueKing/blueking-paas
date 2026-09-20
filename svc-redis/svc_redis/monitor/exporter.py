# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""读取实例 redis-exporter 的指标

redis-exporter 由 redis-operator 作为 sidecar 注入 (需 plan 开启 monitor).
"""

import logging
from dataclasses import dataclass

from kubernetes.client.exceptions import ApiException
from prometheus_client.parser import text_string_to_metric_families

from svc_redis.monitor.entities import RedisInstance
from svc_redis.monitor.utils import request_timeout
from svc_redis.resources.base.base import EnhancedApiClient
from svc_redis.vendor.redis_crd.constants import REDIS_EXPORTER_PORT

logger = logging.getLogger(__name__)

# 需要从 exporter 的样本里挑出来的指标
_USED_MEMORY = "redis_memory_used_bytes"
_MAXMEMORY = "redis_memory_max_bytes"
_CONNECTED_CLIENTS = "redis_connected_clients"
_MAXCLIENTS = "redis_config_maxclients"
_DB_KEYS = "redis_db_keys"


@dataclass(frozen=True)
class ExporterUsage:
    """exporter 中关心的用量, 取不到的字段为 None"""

    used_memory: float | None
    maxmemory: float | None
    connected_clients: float | None
    maxclients: float | None
    db_keys: float | None


def fetch_usage(
    instance: RedisInstance, client: EnhancedApiClient, pod_name: str, deadline: float
) -> ExporterUsage | None:
    """读取实例 exporter 的用量; 取数失败时返回 None"""
    path = f"/api/v1/namespaces/{instance.namespace}/pods/{pod_name}:{REDIS_EXPORTER_PORT}/proxy/metrics"
    try:
        text = client.call_api(
            path,
            "GET",
            auth_settings=["BearerToken"],
            response_type="str",
            _return_http_data_only=True,
            _request_timeout=request_timeout(deadline),
        )
        return _parse_usage(text)
    except ApiException as e:
        logger.warning("unable to fetch exporter metrics of instance<%s>: %s", instance.bk_instance, e)
    except Exception:
        logger.exception("unable to fetch exporter metrics of instance<%s>", instance.bk_instance)
    return None


def _parse_usage(text: str) -> ExporterUsage:
    """从 prometheus 文本中取出关心的样本

    redis_db_keys 带 db 标签, 逐条累加成实例级总量.
    """
    samples: dict[str, float] = {}
    db_keys: list[float] = []
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            if sample.name in (_USED_MEMORY, _MAXMEMORY, _CONNECTED_CLIENTS, _MAXCLIENTS):
                samples[sample.name] = sample.value
            elif sample.name == _DB_KEYS:
                db_keys.append(sample.value)

    return ExporterUsage(
        used_memory=samples.get(_USED_MEMORY),
        maxmemory=samples.get(_MAXMEMORY),
        connected_clients=samples.get(_CONNECTED_CLIENTS),
        maxclients=samples.get(_MAXCLIENTS),
        db_keys=sum(db_keys) if db_keys else None,
    )
