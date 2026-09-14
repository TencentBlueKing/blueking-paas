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

"""本地归属表与网关实际状态的周期性对账。

漂移有三个来源：网关按空闲超时自行回收了沙箱、销毁在网关成功但本地写失败、
创建在网关成功但落库与回滚都失败。前两类让本地记录停留在活跃状态，
第三类在网关侧留下无人认领的孤儿实例。

**对账只收敛状态，任何情况下都不改归属。** 归属是权限判定的唯一依据，
一旦被后台任务改写，越权就成了无人察觉的既成事实。所以这里所有的写操作
都显式限定 update_fields，不碰 application 与 tenant_id。
"""

import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paasng.misc.metrics import E2B_SANDBOX_RECONCILED_COUNTER
from paasng.platform.agent_sandbox.models import E2BSandbox

from .constants import (
    ARCHIVE_BATCH_SIZE,
    SANDBOX_ID_FIELD,
    SANDBOX_STATE_FIELD,
    E2BReconcileOutcome,
    E2BSandboxStatus,
)
from .exceptions import E2BClusterNotConfigured, E2BGatewayError
from .gateway import E2BGatewayClient

logger = logging.getLogger(__name__)

# 记录某个孤儿实例首次被观察到的时刻，安全窗口以此为起点
_ORPHAN_SEEN_KEY = "e2b:orphan-first-seen:{sandbox_id}"


@dataclass
class ClusterReconcileResult:
    """单个集群的对账产出。"""

    skipped: bool = False
    """网关不可达或未登记配置时为 True，其余字段无意义"""

    converged: int = 0
    """状态被收敛的本地记录数"""

    orphans_killed: int = 0
    """已销毁的孤儿实例数"""

    orphans_waiting: int = 0
    """已观察到但尚未过安全窗口的孤儿实例数"""

    failures: int = 0
    """单条处理失败的次数，目前只有销毁孤儿会计入"""


@dataclass
class ReconcileResult:
    """一轮对账的产出，同时用于日志、指标与命令行输出。

    只存各集群结果，聚合数字由 property 按需计算。
    """

    clusters: dict[str, ClusterReconcileResult] = field(default_factory=dict)

    @property
    def clusters_done(self) -> int:
        return sum(1 for r in self.clusters.values() if not r.skipped)

    @property
    def clusters_skipped(self) -> int:
        return sum(1 for r in self.clusters.values() if r.skipped)

    @property
    def skipped_cluster_names(self) -> list[str]:
        return [name for name, r in self.clusters.items() if r.skipped]

    @property
    def converged(self) -> int:
        return sum(r.converged for r in self.clusters.values())

    @property
    def orphans_killed(self) -> int:
        return sum(r.orphans_killed for r in self.clusters.values())

    @property
    def orphans_waiting(self) -> int:
        return sum(r.orphans_waiting for r in self.clusters.values())

    @property
    def failures(self) -> int:
        return sum(r.failures for r in self.clusters.values())


def reconcile_all(dry_run: bool = False) -> ReconcileResult:
    """对所有已启用 e2b 的集群做一轮对账。

    遍历的是集群配置而不是本地记录涉及的集群：孤儿实例在本地没有任何记录，
    只从记录出发就永远发现不了它们。

    :param dry_run: 只计算不写入，用于上线前确认清理范围
    """
    return ReconcileResult(
        clusters={
            cluster_name: reconcile_cluster(cluster_name, dry_run=dry_run) for cluster_name in _enabled_cluster_names()
        }
    )


def reconcile_cluster(cluster_name: str, dry_run: bool = False) -> ClusterReconcileResult:
    """对单个集群做一轮对账。

    某个集群失败不影响其余集群：网关拉不到清单时整个集群跳过，
    这一轮不改动它名下的任何记录。避免由于网关不可达而影响数据面
    """
    try:
        with E2BGatewayClient.for_cluster(cluster_name) as client:
            gateway_items = client.list_sandboxes()
    except (E2BGatewayError, E2BClusterNotConfigured) as exc:
        logger.warning("skip reconciling cluster %s: %s", cluster_name, exc)
        E2B_SANDBOX_RECONCILED_COUNTER.labels(
            cluster=cluster_name, outcome=E2BReconcileOutcome.CLUSTER_SKIPPED.value
        ).inc()
        return ClusterReconcileResult(skipped=True)

    gateway_states = {
        item[SANDBOX_ID_FIELD]: item.get(SANDBOX_STATE_FIELD) for item in gateway_items if item.get(SANDBOX_ID_FIELD)
    }

    killed, waiting, failures = _handle_orphans(cluster_name, set(gateway_states), dry_run=dry_run)
    return ClusterReconcileResult(
        converged=_converge_local_states(cluster_name, gateway_states, dry_run=dry_run),
        orphans_killed=killed,
        orphans_waiting=waiting,
        failures=failures,
    )


def archive_terminated_sandboxes(retention_days: int | None = None, dry_run: bool = False) -> int:
    """删除超过保留期的已终止记录，避免主表无限膨胀。

    :param retention_days: 保留天数，缺省取平台配置
    :returns: 删除的记录数
    """
    days = retention_days if retention_days is not None else settings.AGENT_SANDBOX_E2B_TERMINATED_RETENTION_DAYS
    cutoff = timezone.now() - timezone.timedelta(days=days)

    queryset = E2BSandbox.objects.filter(status=E2BSandboxStatus.TERMINATED.value, updated__lt=cutoff)
    if dry_run:
        return queryset.count()

    total = 0
    while True:
        # 先取一批主键再按主键删。MySQL 不允许 DELETE 的子查询命中同一张表，
        # 直接对切片后的 queryset 调 delete() 也会被 Django 拒绝
        batch = list(queryset.values_list("pk", flat=True)[:ARCHIVE_BATCH_SIZE])
        if not batch:
            break
        deleted, _ = E2BSandbox.objects.filter(pk__in=batch).delete()
        total += deleted

    if total:
        logger.info("archived %d terminated e2b sandbox records older than %d days", total, days)
    return total


def _enabled_cluster_names() -> list[str]:
    return list(ClusterE2BConfig.objects.filter(enabled=True).values_list("cluster__name", flat=True))


def _converge_local_states(cluster_name: str, gateway_states: dict[str, str | None], dry_run: bool) -> int:
    """把本地活跃记录的状态对齐到网关。

    网关侧查不到的记录一律置为已终止——`list` 只返回存活实例，
    不在其中就说明它已经被回收了。
    """
    changed: list[E2BSandbox] = []
    unrecognized: list[str | None] = []
    now = timezone.now()

    for record in E2BSandbox.objects.filter(cluster_name=cluster_name, status__in=E2BSandboxStatus.active_values()):
        target = _target_status(gateway_states, record.sandbox_id)
        if target is None:
            # 状态无法判定，保留本地原状态。网关既然还列出它，它就是活的，
            # 只是活法我们不认识，留着上一个已知状态比改成任何猜测值都更接近事实
            unrecognized.append(gateway_states[record.sandbox_id])
            continue

        if target == record.status:
            continue

        logger.info(
            "converging e2b sandbox %s on cluster %s: %s -> %s", record.sandbox_id, cluster_name, record.status, target
        )
        record.status = target
        # bulk_update 不走 save()，auto_now 不会刷新；归档又按 updated 算保留期，必须显式写
        record.updated = now
        changed.append(record)

    if unrecognized:
        logger.warning(
            "cluster %s: gateway reported %d sandbox(es) in unrecognized states %s, local records left untouched",
            cluster_name,
            len(unrecognized),
            sorted({str(state) for state in unrecognized}),
        )
        E2B_SANDBOX_RECONCILED_COUNTER.labels(
            cluster=cluster_name, outcome=E2BReconcileOutcome.UNKNOWN_STATE.value
        ).inc(len(unrecognized))

    if changed and not dry_run:
        # 只更新状态字段。归属与租户不在列表里，对账改不到它们
        E2BSandbox.objects.bulk_update(changed, ["status", "updated"])

    if changed:
        E2B_SANDBOX_RECONCILED_COUNTER.labels(cluster=cluster_name, outcome=E2BReconcileOutcome.CONVERGED.value).inc(
            len(changed)
        )
    return len(changed)


def _target_status(gateway_states: dict[str, str | None], sandbox_id: str) -> str | None:
    """算出记录应该收敛到的状态。

    :returns: 目标状态，无法判定时为 None
    """
    if sandbox_id not in gateway_states:
        return E2BSandboxStatus.TERMINATED.value

    state = gateway_states[sandbox_id]
    if state in E2BSandboxStatus.get_values():
        return state  # type: ignore[return-value]

    return None


def _handle_orphans(cluster_name: str, gateway_ids: set[str], dry_run: bool) -> tuple[int, int, int]:
    """销毁网关侧存在、本地却没有任何归属记录的实例。

    这类实例不会被任何人列举到，也没人会去销毁它，只会一直占着集群资源。
    一般只会有两类来源：
    1. 网关侧创建成功但本地落库失败 or 回滚销毁失败，这类实例用户无法正常使用
    2. 绕过控制面直接用相同 ApiKey 创建的实例，非预期情况， ApiKey 只应由平台使用

    :returns: (已销毁数, 观察中数, 失败数)
    """
    if not settings.AGENT_SANDBOX_E2B_ORPHAN_CLEANUP_ENABLED:
        return 0, 0, 0

    known_ids = set(E2BSandbox.objects.filter(sandbox_id__in=gateway_ids).values_list("sandbox_id", flat=True))
    # 已终止的本地记录也算"有主"：那是销毁没生效，不是孤儿，重新销毁不归对账管
    orphan_ids = gateway_ids - known_ids
    if not orphan_ids:
        return 0, 0, 0

    killed = waiting = failures = 0
    with E2BGatewayClient.for_cluster(cluster_name) as client:
        for sandbox_id in sorted(orphan_ids):
            if not _orphan_passed_safety_window(sandbox_id, dry_run=dry_run):
                waiting += 1
                continue

            if dry_run:
                killed += 1
                continue

            try:
                client.kill_sandbox(sandbox_id)
            except E2BGatewayError:
                failures += 1
                logger.exception("failed to kill orphan e2b sandbox %s on cluster %s", sandbox_id, cluster_name)
                E2B_SANDBOX_RECONCILED_COUNTER.labels(
                    cluster=cluster_name, outcome=E2BReconcileOutcome.ORPHAN_KILL_FAILED.value
                ).inc()
                continue

            killed += 1
            cache.delete(_ORPHAN_SEEN_KEY.format(sandbox_id=sandbox_id))
            logger.warning("killed orphan e2b sandbox %s on cluster %s", sandbox_id, cluster_name)
            E2B_SANDBOX_RECONCILED_COUNTER.labels(
                cluster=cluster_name, outcome=E2BReconcileOutcome.ORPHAN_KILLED.value
            ).inc()

    return killed, waiting, failures


def _orphan_passed_safety_window(sandbox_id: str, dry_run: bool) -> bool:
    """判断某个孤儿是否已经孤立得足够久，可以销毁"""
    window = settings.AGENT_SANDBOX_E2B_ORPHAN_SAFETY_WINDOW_MINUTES * 60
    key = _ORPHAN_SEEN_KEY.format(sandbox_id=sandbox_id)

    first_seen = cache.get(key)
    if first_seen is None:
        if not dry_run:
            # TTL 取窗口的三倍：够跨过窗口，又不会让早已消失的实例长期占着键
            cache.set(key, time.time(), timeout=window * 3)
        logger.info("observed orphan e2b sandbox %s for the first time, waiting out the safety window", sandbox_id)
        return False

    return time.time() - first_seen >= window
