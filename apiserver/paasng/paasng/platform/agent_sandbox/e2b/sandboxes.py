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

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paasng.platform.agent_sandbox.models import E2BSandbox
from paasng.platform.applications.models import Application

from .clusters import select_e2b_cluster
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

    with E2BGatewayClient.for_cluster(cluster.name) as client:
        resp = client.create_sandbox(payload)

        # 从这里开始沙箱已在网关侧存在。后面任何一步失败都必须销毁它，
        # 否则会留下一个本地无记录、用户看不到、也没人回收的孤儿实例
        try:
            _record_ownership(application, cluster.name, resp)
        except Exception:
            _rollback_created_sandbox(client, resp.get(SANDBOX_ID_FIELD))
            raise

        return _rewrite_data_plane_address(resp, client.config)


def get_sandbox(application: Application, sandbox_id: str) -> dict[str, Any]:
    """查询沙箱详情。

    :returns: 预期网关详情响应，``domain`` 已改写为该集群的对外地址。其余字段原样透传，
        字段名是 e2b 协议规定的驼峰形式。相对 list，详情多出连数据面所需的两项：

        - ``sandboxID``：沙箱标识
        - ``templateID``：创建时用的模板
        - ``state``：网关侧运行态（``running`` / ``paused`` 等）
        - ``startedAt`` / ``endAt``：实例启动与预计回收时间
        - ``cpuCount`` / ``memoryMB`` / ``diskSizeMB``：规格
        - ``envdVersion``：数据面 envd 版本
        - ``clientID``：网关签发的客户端标识
        - ``domain``：数据面入口域名，由平台换成 ``ClusterE2BConfig.data_plane_address``
        - ``envdAccessToken``：本次重新签发的沙箱访问令牌，过期后续期靠再调 get，
          不可缓存旧值

    :raises E2BSandboxNotFound: 沙箱不存在、不属于该应用，或本地已标记为终止
    """
    sandbox = _get_live_sandbox(application, sandbox_id)

    with E2BGatewayClient.for_cluster(sandbox.cluster_name) as client:
        try:
            resp = client.get_sandbox(sandbox_id)
        except E2BGatewayNotFound as exc:
            # 本地还有记录而网关侧已不存在，多半是被超时回收了。
            # 这里只做转译，本地状态的收敛交给对账任务，避免读路径写库
            raise E2BSandboxNotFound(f"sandbox {sandbox_id} is gone on gateway") from exc

        return _rewrite_data_plane_address(resp, client.config)


def list_sandboxes(application: Application) -> list[dict[str, Any]]:
    """列出该应用名下仍然存活的沙箱。

    以本地归属表为准，向各集群网关取运行态后求交。不能直接透传网关的列表：
    那是平台统一凭证的全集，会把其他租户的沙箱一并暴露出去。

    某个集群不可达时跳过该集群，不影响其余集群的结果。

    :returns: 求交后的网关列表条目。每条字段原样透传，不做数据面地址改写——
        列表本身不含 ``domain`` / ``envdAccessToken``，SDK 连数据面要再走 get。
        字段名是 e2b 协议规定的驼峰形式，SDK 的 ``ListedSandbox.from_dict``
        缺任一必填项都会整表反序列化失败：

        - ``sandboxID``：沙箱标识
        - ``templateID``：创建时用的模板
        - ``state``：网关侧运行态（``running`` / ``paused`` 等）
        - ``startedAt`` / ``endAt``：实例启动与预计回收时间
        - ``cpuCount`` / ``memoryMB`` / ``diskSizeMB``：规格
        - ``envdVersion``：数据面 envd 版本
        - ``clientID``：网关签发的客户端标识
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
            with E2BGatewayClient.for_cluster(cluster_name) as client:
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

    with E2BGatewayClient.for_cluster(sandbox.cluster_name) as client:
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

    with E2BGatewayClient.for_cluster(sandbox.cluster_name) as client:
        try:
            client.set_timeout(sandbox_id, timeout)
        except E2BGatewayNotFound as exc:
            raise E2BSandboxNotFound(f"sandbox {sandbox_id} is gone on gateway") from exc


def _rewrite_data_plane_address(resp: dict[str, Any], config: ClusterE2BConfig) -> dict[str, Any]:
    """把网关响应里的数据面地址换成该集群的对外入口。

    网关填的是集群内 Service 域名（如 ``e2b-sandbox-gateway.bcs-system.svc.cluster.local``），
    集群外 SDK 解析不到。SDK 会采用控制面返回的 domain 拼数据面 URL
    （``https://<端口>-<沙箱ID>.<domain>``），本地 ``E2B_DOMAIN`` 只在该字段为空时兜底。
    因此必须改写成 ``config.data_plane_address`` 上登记的对外地址；不同集群
    改写出不同域名，客户端就被导向对应入口。
    """
    resp[DATA_PLANE_DOMAIN_FIELD] = config.data_plane_address
    return resp


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
