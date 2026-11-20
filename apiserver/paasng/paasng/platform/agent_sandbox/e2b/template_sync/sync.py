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

"""向集群下发模板的 CR，并按结果更新下发状态。"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.platform.agent_sandbox.e2b.clusters import list_enabled_e2b_configs, resolve_template_targets
from paasng.platform.agent_sandbox.e2b.constants import TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate
from paasng.utils.lock import redis_lock

from .resources import TemplateResources
from .states import prune_sync_states, save_sync_state, truncate_message

logger = logging.getLogger(__name__)

SYNC_LOCK_KEY = "lock:sync_e2b_templates"


@dataclass
class ClusterSyncResult:
    """单个集群的同步结果

    :param synced: 下发成功的资源名
    :param failed: 下发失败的资源名到失败原因的映射
    :param pruned: 因数据库中已不存在而被清理的资源名
    :param error: 集群级别的失败（如连不上集群），非空时其余字段可能不完整
    """

    cluster_name: str
    synced: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    pruned: list[str] = field(default_factory=list)
    error: str = ""


def sync_templates(
    cluster_names: set[str] | None = None, resource_names: set[str] | None = None
) -> list[ClusterSyncResult]:
    """把模板下发到启用 e2b 的集群，并清理数据库中已不存在的模板留下的 CR。

    范围内的下发状态按本次结果重写。幂等，可重复调用。某个集群失败不影响其余集群。

    :param cluster_names: 只下发到这些集群，为空表示全部启用 e2b 的集群
    :param resource_names: 只下发这些模板，为空表示全部模板。限定模板时只清理范围内已删除模板的 CR：
        只拿到一部分模板，判断不了集群里其余多出来的 CR 是不是已删除模板的残留
    :raises E2BTemplateSyncInProgress: 另一次下发还没结束，调用方须稍后重试，否则模板会停在待同步
    """
    with _sync_lock():
        return _sync_templates(cluster_names, resource_names)


def _sync_templates(cluster_names: set[str] | None, resource_names: set[str] | None) -> list[ClusterSyncResult]:
    # 这份列表只决定下发哪些模板、各下发到哪些集群，真正下发时以重新读库为准
    query = E2BSandboxTemplate.objects.select_related("application")
    if resource_names is not None:
        query = query.filter(resource_name__in=resource_names)
    templates = list(query)
    configs = list_enabled_e2b_configs()
    # 目标集群按全部启用 e2b 的集群求，只限定下发范围，否则范围外集群的状态会被当成不再是目标而删掉
    targets = resolve_template_targets(templates, {c.cluster.name for c in configs})

    if cluster_names is not None:
        configs = [c for c in configs if c.cluster.name in cluster_names]
    results = []
    for config in configs:
        # 计算当前集群相关的模板
        cluster_templates = [t for t in templates if config.cluster.name in targets[t.resource_name]]
        results.append(_sync_cluster(config, cluster_templates, prune_scope=resource_names))

    prune_sync_states(templates, targets)
    return results


def _sync_cluster(
    config: ClusterE2BConfig, templates: list[E2BSandboxTemplate], prune_scope: set[str] | None
) -> ClusterSyncResult:
    """同步指定集群下的模板
    :param prune_scope: 只清理这些资源名中已删除模板的 CR，为空表示清理全部
    """
    cluster_name = config.cluster.name
    result = ClusterSyncResult(cluster_name=cluster_name)
    try:
        with get_client_by_cluster_name(cluster_name) as client:
            resources = TemplateResources(client, config.namespace)
            _apply_templates(resources, cluster_name, templates, result)
            result.pruned = _prune(resources, prune_scope)
    except Exception as exc:
        logger.exception("failed to sync e2b templates to cluster %s", cluster_name)
        result.error = truncate_message(str(exc))
        # 连不上集群时还没处理到的模板，同样记为失败，否则会残留成功或待同步的旧状态
        for snapshot in templates:
            if snapshot.resource_name not in result.synced and snapshot.resource_name not in result.failed:
                save_sync_state(snapshot, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
    return result


def _apply_templates(
    resources: TemplateResources,
    cluster_name: str,
    templates: list[E2BSandboxTemplate],
    result: ClusterSyncResult,
) -> None:
    """逐个下发模板并更新下发状态，单个模板失败不影响其余模板。

    边下发边写入 ``result``：中途连不上集群时，调用方据此判断哪些模板还没处理
    """
    for snapshot in templates:
        # 再读一遍库，避免中途被修改
        template = _reload(snapshot)
        if template is None:
            continue
        try:
            resources.apply(template)
        except Exception as exc:
            logger.exception("failed to sync e2b template %s to cluster %s", template.resource_name, cluster_name)
            result.failed[template.resource_name] = truncate_message(str(exc))
            save_sync_state(template, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
        else:
            result.synced.append(template.resource_name)
            save_sync_state(template, cluster_name, E2BTemplateSyncStatus.SUCCEEDED)


@contextmanager
def _sync_lock() -> Iterator[None]:
    # TODO: 锁没有续期，一次下发超过 TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS（模板多的全量同步可能做到）时会提前过期：
    with redis_lock(SYNC_LOCK_KEY, timeout=TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS) as acquired:
        if not acquired:
            raise E2BTemplateSyncInProgress("another e2b template sync is running")
        yield


def _reload(template: E2BSandboxTemplate) -> E2BSandboxTemplate | None:
    """下发前重新读库：已删除的返回空，已修改的返回最新状态。

    锁提前过期时，别的下发可能已经用更新的状态写过集群，用手上的旧对象会把它覆盖回去
    """
    return E2BSandboxTemplate.objects.select_related("application").filter(pk=template.pk).first()


def _prune(resources: TemplateResources, scope: set[str] | None) -> list[str]:
    """清理由平台管理、但数据库中已不存在的模板留下的 CR。

    模板仍在、但集群已不再是它的目标（自定义模板的分配集群被下掉）时，CR 不会清理，需要手动删除

    :param scope: 只清理这些资源名，为空表示集群里全部平台管理的 CR
    :returns: 被清理的资源名
    """
    if scope is None:
        scope = resources.list_managed()
    # 先列出 CR 再查库：同步期间新建并下发完成的模板，查库时已能看到，不会被误删
    known = set(E2BSandboxTemplate.objects.filter(resource_name__in=scope).values_list("resource_name", flat=True))
    return [name for name in sorted(scope - known) if resources.delete(name)]
