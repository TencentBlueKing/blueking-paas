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

"""e2b 控制面的编排层：选集群、转发网关、落库归属、改写数据面地址"""

import logging
from collections import defaultdict
from typing import Any

from django.utils.dateparse import parse_datetime

from paasng.platform.agent_sandbox.models import E2BSandbox
from paasng.platform.applications.models import Application

from .clusters import get_e2b_cluster_config, select_e2b_cluster
from .constants import (
    DATA_PLANE_DOMAIN_FIELD,
    SANDBOX_ID_FIELD,
    E2BSandboxStatus,
)
from .exceptions import (
    E2BClusterNotConfigured,
    E2BGatewayError,
    E2BGatewayNotFound,
    E2BSandboxNotFound,
)
from .gateway import E2BGatewayClient

logger = logging.getLogger(__name__)


def create_sandbox(application: Application, payload: dict[str, Any]) -> dict[str, Any]:
    """创建沙箱并登记归属。

    :param application: 归属应用，由 API Key 认证后端解析得出
    :param payload: 透传给网关的创建请求体
    :returns: 网关响应，数据面地址字段已改写为该集群的对外地址
    :raises E2BClusterUnavailable: 没有可用于 e2b 的集群
    :raises E2BGatewayTimeout: 网关未在创建超时窗口内返回
    """
    cluster = select_e2b_cluster(application.tenant_id, application.region)
    config = get_e2b_cluster_config(cluster.name)

    with E2BGatewayClient(config) as client:
        resp = client.create_sandbox(payload)

        # 从这里开始沙箱已在网关侧存在。后面任何一步失败都必须销毁它，
        # 否则会留下一个本地无记录、用户看不到、也没人回收的孤儿实例
        try:
            _record_ownership(application, cluster.name, resp)
        except Exception:
            _rollback_created_sandbox(client, resp.get(SANDBOX_ID_FIELD))
            raise

    # 改写数据面地址字段
    resp[DATA_PLANE_DOMAIN_FIELD] = config.data_plane_address
    return resp


def get_sandbox(application: Application, sandbox_id: str) -> dict[str, Any]:
    """查询沙箱详情。

    :raises E2BSandboxNotFound: 沙箱不存在、不属于该应用，或本地已标记为终止
    """
    sandbox = _get_live_sandbox(application, sandbox_id)
    config = get_e2b_cluster_config(sandbox.cluster_name)

    with E2BGatewayClient(config) as client:
        try:
            resp = client.get_sandbox(sandbox_id)
        except E2BGatewayNotFound as exc:
            # 本地还有记录而网关侧已不存在，多半是被超时回收了。
            # 这里只做转译，本地状态的收敛交给对账任务，避免读路径写库
            raise E2BSandboxNotFound(f"sandbox {sandbox_id} is gone on gateway") from exc

    # 改写数据面地址字段
    resp[DATA_PLANE_DOMAIN_FIELD] = config.data_plane_address
    return resp


def list_sandboxes(application: Application) -> list[dict[str, Any]]:
    """列出该应用名下仍然存活的沙箱。

    以本地归属表为准，向各集群网关取运行态后求交。不能直接透传网关的列表：
    那是平台统一凭证的全集，会把其他租户的沙箱一并暴露出去。

    某个集群不可达时跳过该集群，不影响其余集群的结果
    """
    owned = _live_sandboxes(application)
    if not owned:
        return []

    ids_by_cluster: dict[str, set[str]] = defaultdict(set)
    for sandbox in owned:
        ids_by_cluster[sandbox.cluster_name].add(sandbox.sandbox_id)

    items: list[dict[str, Any]] = []
    for cluster_name, owned_ids in ids_by_cluster.items():
        try:
            config = get_e2b_cluster_config(cluster_name)
            with E2BGatewayClient(config) as client:
                cluster_items = client.list_sandboxes()
        except (E2BGatewayError, E2BClusterNotConfigured) as exc:
            logger.warning(
                "skip cluster %s while listing e2b sandboxes for app %s: %s", cluster_name, application.code, exc
            )
            continue

        for item in cluster_items:
            if item.get(SANDBOX_ID_FIELD) in owned_ids:
                items.append(item)

    return items


def kill_sandbox(application: Application, sandbox_id: str) -> None:
    """销毁沙箱，幂等。

    :raises E2BSandboxNotFound: 沙箱不存在或不属于该应用
    """
    sandbox = E2BSandbox.objects.get_owned(application, sandbox_id)
    if sandbox.status == E2BSandboxStatus.TERMINATED.value:
        # 已销毁过，不必再打网关
        return

    config = get_e2b_cluster_config(sandbox.cluster_name)
    with E2BGatewayClient(config) as client:
        try:
            client.kill_sandbox(sandbox_id)
        except E2BGatewayNotFound:
            # 网关侧已经没有了，目标状态已经达成
            logger.info("sandbox %s already gone on gateway, marking terminated locally", sandbox_id)

    try:
        sandbox.status = E2BSandboxStatus.TERMINATED.value
        sandbox.save(update_fields=["status", "updated"])
    except Exception:
        # 网关侧已经销毁成功，对用户而言操作已完成，不该因为本地写失败而报错。
        # 留下的状态漂移由对账任务纠正
        logger.exception("failed to mark sandbox %s terminated after gateway kill", sandbox_id)


def set_sandbox_timeout(application: Application, sandbox_id: str, timeout: int) -> None:
    """重设沙箱存活时长。

    :raises E2BSandboxNotFound: 沙箱不存在、不属于该应用，或本地已标记为终止
    """
    sandbox = _get_live_sandbox(application, sandbox_id)
    config = get_e2b_cluster_config(sandbox.cluster_name)

    with E2BGatewayClient(config) as client:
        try:
            client.set_timeout(sandbox_id, timeout)
        except E2BGatewayNotFound as exc:
            raise E2BSandboxNotFound(f"sandbox {sandbox_id} is gone on gateway") from exc


def _get_live_sandbox(application: Application, sandbox_id: str) -> E2BSandbox:
    """取归属于该应用且未终止的沙箱记录"""
    sandbox = E2BSandbox.objects.get_owned(application, sandbox_id)
    if sandbox.status == E2BSandboxStatus.TERMINATED.value:
        raise E2BSandboxNotFound(f"sandbox {sandbox_id} has been terminated")
    return sandbox


def _live_sandboxes(application: Application) -> list[E2BSandbox]:
    return list(
        E2BSandbox.objects.owned_by(application).filter(
            status__in=E2BSandboxStatus.active_values(),
        )
    )


def _record_ownership(application: Application, cluster_name: str, resp: dict[str, Any]) -> None:
    E2BSandbox.objects.create(
        sandbox_id=resp[SANDBOX_ID_FIELD],
        application=application,
        cluster_name=cluster_name,
        template_id=resp.get("templateID", ""),
        expired_at=parse_datetime(resp["endAt"]) if resp.get("endAt") else None,
        tenant_id=application.tenant_id,
    )


def _rollback_created_sandbox(client: E2BGatewayClient, sandbox_id: str | None) -> None:
    """销毁已在网关侧创建、但未能完成登记的沙箱。

    尽力而为：回滚本身失败也不能掩盖原始异常，否则用户看到的是一个与根因无关的报错。
    这种情况会留下孤儿实例，交由对账任务兜底，所以这里用 exception 级别记录。
    """
    if not sandbox_id:
        return

    try:
        client.kill_sandbox(sandbox_id)
    except Exception:
        logger.exception("failed to roll back orphan e2b sandbox %s, leaving it to the reconcile task", sandbox_id)
