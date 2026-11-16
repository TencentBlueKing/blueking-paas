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

"""向集群下发模板的 CR，并按结果更新下发记录。"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from paas_wl.bk_app.agent_sandbox.constants import SANDBOX_INSTANCE_API_VERSION
from paas_wl.infras.cluster.models import ClusterE2BConfig
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.e2b.clusters import TemplateTargetResolver, list_enabled_e2b_configs
from paasng.platform.agent_sandbox.e2b.constants import TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate
from paasng.utils.lock import redis_lock

from .manifests import (
    build_pool_manifest,
    build_template_manifest,
    build_template_patch,
    is_managed,
    managed_labels,
)
from .records import prune_records, record_status, truncate_message

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

    范围内的下发记录按本次结果重写。幂等，可重复调用。某个集群失败不影响其余集群。

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
    # 目标集群按全部启用 e2b 的集群求，只限定下发范围，否则范围外集群的记录会被当成不再是目标而删掉
    resolver = TemplateTargetResolver({c.cluster.name for c in configs})
    # 计算模板需要下发到哪些集群
    targets = {t.resource_name: resolver.resolve(t) for t in templates}

    if cluster_names is not None:
        configs = [c for c in configs if c.cluster.name in cluster_names]
    results = []
    for config in configs:
        # 计算当前集群相关的模板
        cluster_templates = [t for t in templates if config.cluster.name in targets[t.resource_name]]
        results.append(_sync_cluster(config, cluster_templates, prune_scope=resource_names))

    prune_records(templates, targets)
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
            for snapshot in templates:
                # 再读一遍库，避免中途被修改
                template = _reload(snapshot)
                if template is None:
                    continue
                try:
                    _apply_resources(client, template, config.namespace)
                except Exception as exc:
                    logger.exception(
                        "failed to sync e2b template %s to cluster %s", template.resource_name, cluster_name
                    )
                    result.failed[template.resource_name] = truncate_message(str(exc))
                    record_status(template, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
                else:
                    result.synced.append(template.resource_name)
                    record_status(template, cluster_name, E2BTemplateSyncStatus.SUCCEEDED)

            # 回收被删除模板的残留 CR
            known_resource_names = set(E2BSandboxTemplate.objects.values_list("resource_name", flat=True))
            if prune_scope is None:
                result.pruned = _prune(client, config.namespace, known_resource_names)
            else:
                deleted = sorted(prune_scope - known_resource_names)
                result.pruned = [name for name in deleted if _delete_managed(client, name, config.namespace)]
    except Exception as exc:
        logger.exception("failed to sync e2b templates to cluster %s", cluster_name)
        result.error = truncate_message(str(exc))
        # 连不上集群时还没处理到的模板，同样记为失败，否则会残留成功或待同步的旧状态
        for snapshot in templates:
            if snapshot.resource_name not in result.synced and snapshot.resource_name not in result.failed:
                record_status(snapshot, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
    return result


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


# 集群资源操作


def _apply_resources(client: EnhancedApiClient, template: E2BSandboxTemplate, namespace: str) -> None:
    """创建或更新模板的 CR。先模板后池子，池子引用的模板必须先存在"""
    name = template.resource_name
    _create_or_patch(
        _kres(kres.KSandboxTemplate, client),
        name,
        namespace,
        manifest=build_template_manifest(template, namespace),
        patch=build_template_patch(template, namespace),
    )
    pool = build_pool_manifest(template, namespace)
    _create_or_patch(_kres(kres.KSandboxPool, client), name, namespace, manifest=pool, patch=pool)


def _create_or_patch(res: kres.BaseKresource, name: str, namespace: str, manifest: dict, patch: dict) -> None:
    """不存在时按清单创建，已存在时以 merge patch 更新。

    不用 replace：整体覆盖会清掉控制器写在对象上的 finalizers、annotations 等元数据
    """
    try:
        res.get(name, namespace=namespace)
    except ResourceMissing:
        res.create(name, body=manifest, namespace=namespace)
    else:
        res.patch(name, body=patch, namespace=namespace, ptype=kres.PatchType.MERGE)


def _delete_managed(client: EnhancedApiClient, resource_name: str, namespace: str) -> bool:
    """删除平台管理的同名 CR，先池子后模板。不带平台标签的 CR 原样保留。

    :returns: 是否删除了任何 CR
    """
    deleted = False
    for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate):
        res = _kres(kres_cls, client)
        try:
            obj = res.get(resource_name, namespace=namespace)
        except ResourceMissing:
            continue
        if not is_managed(obj.to_dict()):
            logger.warning(
                "%s %s/%s is not managed by platform, skip deleting", kres_cls.kind, namespace, resource_name
            )
            continue
        res.delete(resource_name, namespace=namespace)
        deleted = True
    return deleted


def _prune(client: EnhancedApiClient, namespace: str, known_resource_names: set[str]) -> list[str]:
    """清理由平台管理、但数据库中已不存在的模板留下的 CR。

    模板仍在、但集群已不再是它的目标（自定义模板的分配集群被下掉）时，CR 不会清理，需要手动删除
    """
    selector = managed_labels()
    stale: set[str] = set()
    for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate):
        for item in _kres(kres_cls, client).ops_batch.list(labels=selector, namespace=namespace).items:
            if item.metadata.name not in known_resource_names:
                stale.add(item.metadata.name)

    pruned = []
    for name in sorted(stale):
        if _delete_managed(client, name, namespace):
            pruned.append(name)
    return pruned


def _kres(kres_cls: type[kres.BaseKresource], client: EnhancedApiClient) -> kres.BaseKresource:
    return kres_cls(client, api_version=SANDBOX_INSTANCE_API_VERSION)
