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

"""已分配实例的清单

只包含开启 monitor 套餐创建的实例 (有 redis-exporter sidecar), 并带上套餐内存上限
(Redis 未设置 maxmemory 时的使用率分母).
"""

import json
import logging
from typing import NamedTuple

from kubernetes.utils.quantity import parse_quantity
from paas_service.models import ServiceInstance, ServiceInstanceConfig

from svc_redis.monitor.entities import RedisInstance

logger = logging.getLogger(__name__)


class AllocatedInstance(NamedTuple):
    """一个已分配实例及其套餐内存上限"""

    instance: RedisInstance
    memory_limit: int | None


def list_allocated_instances() -> list[AllocatedInstance]:
    """全部已分配 (未回收) 实例; 单个实例解析失败只跳过自己"""
    # credentials 是加密字段, 读取即解密; 采集用不到它, 使用 only() 显式获取需要字段
    rows = list(
        ServiceInstance.objects.filter(to_be_deleted=False)
        .select_related("plan")
        .only("uuid", "config", "plan_id", "plan__config")
    )
    app_infos = {
        str(config.instance_id): config.paas_app_info
        for config in ServiceInstanceConfig.objects.filter(instance_id__in=[row.uuid for row in rows]).only(
            "instance_id", "paas_app_info"
        )
    }

    allocated: list[AllocatedInstance] = []
    for row in rows:
        try:
            item = _build_instance(row, app_infos.get(str(row.uuid)) or {})
        except Exception:
            logger.exception("unable to build the redis instance<%s>", row.uuid)
            continue
        if item is not None:
            allocated.append(item)
    return allocated


def _build_instance(service_instance: ServiceInstance, app_info: dict) -> AllocatedInstance | None:
    """由平台分配记录构建实例身份与套餐内存上限; 无法解析的实例 (如 client-side 实例) 返回 None"""
    if service_instance.plan is None:
        logger.warning("skip client-side redis instance<%s> which has no plan", service_instance.uuid)
        return None

    plan_config = json.loads(service_instance.plan.config or "{}")
    # 未开启 monitor 的套餐创建的实例没有 redis-exporter, 采集不到 exporter 指标, 不纳入监控
    if not plan_config.get("monitor"):
        logger.debug("skip redis instance<%s> whose plan has monitor disabled", service_instance.uuid)
        return None

    cluster_name = plan_config.get("cluster_name")
    if not cluster_name:
        logger.warning("no cluster_name found in plan config of redis instance<%s>", service_instance.uuid)
        return None

    return AllocatedInstance(
        instance=RedisInstance(
            bk_instance=str(service_instance.uuid),
            bk_cluster=str(cluster_name),
            namespace=str(service_instance.config.get("namespace") or ""),
            bk_app_code=str(app_info.get("app_code", "")),
            bk_module=str(app_info.get("module", "")),
            bk_env=str(app_info.get("environment", "")),
        ),
        memory_limit=_parse_memory_size(plan_config.get("memory_size")),
    )


def _parse_memory_size(memory_size) -> int | None:
    """将套餐中的内存上限 (如 "2Gi") 解析为字节数"""
    if not memory_size:
        return None

    try:
        return int(parse_quantity(str(memory_size)))
    except (ValueError, TypeError):
        logger.warning("unable to parse memory size: %s", memory_size)
        return None
