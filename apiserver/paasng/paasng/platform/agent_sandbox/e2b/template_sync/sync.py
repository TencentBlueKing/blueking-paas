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

"""向集群下发模板的 CR，并维护各集群的下发记录。

下发是幂等的 upsert，失败的集群只记录结果、不回滚，由平台管理端的手动同步补齐。

全量同步与单模板同步共用一把全局锁，拿到锁之后才读库，因此最后执行的一方用的总是最新状态。
锁只串行化向集群的下发，模板的增删改只写库、投递任务，不受影响。代价是下发排队：
单模板下发只需秒级，撞上时多等一轮重试；全量同步期间保存的模板，要等它结束才下发。
模板保存频率低，不值得为此按模板拆锁。
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from paas_wl.bk_app.agent_sandbox.constants import SANDBOX_INSTANCE_API_VERSION
from paas_wl.infras.cluster.models import ClusterE2BConfig
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.e2b.clusters import (
    TemplateTargetResolver,
    list_enabled_e2b_cluster_names,
    list_enabled_e2b_configs,
)
from paasng.platform.agent_sandbox.e2b.constants import TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BTemplateSyncInProgress
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.utils.lock import redis_lock

from .manifests import build_pool_manifest, build_template_manifest, is_managed, managed_labels, spec_digest
from .status import is_current

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


# 下发


def sync_template(resource_name: str) -> None:
    """把单个模板的当前状态下发到它的目标集群，模板保存或删除后异步调用。

    模板已从数据库删除时，从所有启用 e2b 的集群里删掉它的 CR。

    :raises E2BTemplateSyncInProgress: 另一次下发还没结束，调用方须稍后重试，否则模板会停在待同步
    """
    with _sync_lock():
        _sync_template(resource_name)


def _sync_template(resource_name: str) -> None:
    template = E2BSandboxTemplate.objects.select_related("application").filter(resource_name=resource_name).first()
    if template is None:
        for config in list_enabled_e2b_configs():
            try:
                with get_client_by_cluster_name(config.cluster.name) as client:
                    _delete_managed(client, resource_name, config.namespace)
            except Exception:
                logger.exception(
                    "failed to delete e2b template %s from cluster %s", resource_name, config.cluster.name
                )
        return

    configs = list_enabled_e2b_configs()
    # 目标集群可能在保存之后有变化，以下发时为准
    target_names = TemplateTargetResolver({c.cluster.name for c in configs}).resolve(template)
    _delete_non_target_records(template, target_names)
    for config in configs:
        if config.cluster.name not in target_names:
            continue
        template = _reload(template)
        if template is None:
            return
        try:
            with get_client_by_cluster_name(config.cluster.name) as client:
                _apply(client, template, config.namespace)
        except Exception as exc:
            logger.exception("failed to sync e2b template %s to cluster %s", resource_name, config.cluster.name)
            _record(template, config.cluster.name, E2BTemplateSyncStatus.FAILED, str(exc))
        else:
            _record(template, config.cluster.name, E2BTemplateSyncStatus.SUCCEEDED)


def sync_all(cluster_names: set[str] | None = None, resource_names: set[str] | None = None) -> list[ClusterSyncResult]:
    """把模板下发到启用 e2b 的集群，并清理数据库中已不存在的模板留下的 CR。

    范围内的下发记录按本次结果重写。幂等，可重复调用。某个集群失败不影响其余集群。

    :param cluster_names: 只下发到这些集群，为空表示全部启用 e2b 的集群
    :param resource_names: 只下发这些模板，为空表示全部模板。限定模板时不做清理：
        只拿到一部分模板，判断不了集群里多出来的 CR 是不是已删除模板的残留
    :raises E2BTemplateSyncInProgress: 另一次下发还没结束
    """
    with _sync_lock():
        return _sync_all(cluster_names, resource_names)


def _sync_all(cluster_names: set[str] | None, resource_names: set[str] | None) -> list[ClusterSyncResult]:
    # 这份列表只决定下发哪些模板、各下发到哪些集群，真正下发时以重新读库为准
    templates_qs = E2BSandboxTemplate.objects.select_related("application")
    if resource_names is not None:
        templates_qs = templates_qs.filter(resource_name__in=resource_names)
    templates = list(templates_qs)
    configs = list_enabled_e2b_configs()
    # 目标集群按全部启用 e2b 的集群求，只限定下发范围，否则范围外集群的记录会被当成不再是目标而删掉
    resolver = TemplateTargetResolver({c.cluster.name for c in configs})
    targets = {t.resource_name: resolver.resolve(t) for t in templates}
    # 如果集群下线，则关联的同步记录需要清理
    for snapshot in templates:
        _delete_non_target_records(snapshot, targets[snapshot.resource_name])

    if cluster_names is not None:
        configs = [c for c in configs if c.cluster.name in cluster_names]
    results = []
    for config in configs:
        cluster_templates = [t for t in templates if config.cluster.name in targets[t.resource_name]]
        results.append(_sync_cluster(config, cluster_templates, prune=resource_names is None))

    E2BSandboxTemplateSyncRecord.objects.exclude(template_id__in=E2BSandboxTemplate.objects.values("pk")).delete()
    return results


def _sync_cluster(config: ClusterE2BConfig, templates: list[E2BSandboxTemplate], prune: bool) -> ClusterSyncResult:
    cluster_name = config.cluster.name
    result = ClusterSyncResult(cluster_name=cluster_name)
    try:
        with get_client_by_cluster_name(cluster_name) as client:
            for snapshot in templates:
                # 同步途中被删除的模板跳过，被修改的按最新配置下发
                template = _reload(snapshot)
                if template is None:
                    continue
                try:
                    _apply(client, template, config.namespace)
                except Exception as exc:
                    logger.exception(
                        "failed to sync e2b template %s to cluster %s", template.resource_name, cluster_name
                    )
                    result.failed[template.resource_name] = _truncate(str(exc))
                    _record(template, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
                else:
                    result.synced.append(template.resource_name)
                    _record(template, cluster_name, E2BTemplateSyncStatus.SUCCEEDED)

            # 回收被删除模板的残留 CR
            if prune:
                known_resource_names = set(E2BSandboxTemplate.objects.values_list("resource_name", flat=True))
                result.pruned = _prune(client, config.namespace, known_resource_names)
    except Exception as exc:
        logger.exception("failed to sync e2b templates to cluster %s", cluster_name)
        result.error = _truncate(str(exc))
        # 连不上集群时还没处理到的模板，同样记为失败，否则会残留成功或待同步的旧状态
        for snapshot in templates:
            if snapshot.resource_name not in result.synced and snapshot.resource_name not in result.failed:
                _record(snapshot, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
    return result


@contextmanager
def _sync_lock() -> Iterator[None]:
    with redis_lock(SYNC_LOCK_KEY, timeout=TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS) as acquired:
        if not acquired:
            raise E2BTemplateSyncInProgress("another e2b template sync is running")
        yield


def _reload(template: E2BSandboxTemplate) -> E2BSandboxTemplate | None:
    """下发前重新读库：已删除的返回空，已修改的返回最新状态。

    锁提前过期时，别的下发可能已经用更新的状态写过集群，用手上的旧对象会把它覆盖回去
    """
    return E2BSandboxTemplate.objects.select_related("application").filter(pk=template.pk).first()


# 下发记录。除下发本身外，模板保存、投递同步任务、集群下线时也要改记录，入口都在这里


def mark_pending(template: E2BSandboxTemplate) -> None:
    """模板保存后、下发前调用：目标集群全部置为待同步，不再是目标的集群的记录删除"""
    target_names = TemplateTargetResolver(list_enabled_e2b_cluster_names()).resolve(template)
    _delete_non_target_records(template, target_names)
    for cluster_name in target_names:
        _record(template, cluster_name, E2BTemplateSyncStatus.PENDING)


def mark_sync_pending(cluster_names: set[str] | None = None, resource_names: set[str] | None = None) -> None:
    """投递同步任务前调用：范围内已有的记录置为待同步，概览里没有待同步即同步完成。参数同 ``sync_all``。

    已经成功下发了当前配置的记录不动：重新同步写的还是同一份配置，同步期间模板应当保持可用，
    真失败了再由同步改成失败。

    没有记录的目标集群在概览里本就算未完成，不再是目标的集群不计入概览、由同步删除，
    所以只需改已有的记录
    """
    records = E2BSandboxTemplateSyncRecord.objects.select_related("template")
    if cluster_names is not None:
        records = records.filter(cluster_name__in=cluster_names)
    if resource_names is not None:
        records = records.filter(template__resource_name__in=resource_names)
    stale = [r.pk for r in records if not is_current(r, r.template)]
    E2BSandboxTemplateSyncRecord.objects.filter(pk__in=stale).update(
        status=E2BTemplateSyncStatus.PENDING.value, message=""
    )


def forget_cluster(cluster_name: str) -> None:
    """集群的 e2b 配置删除后调用：删掉该集群的全部下发记录。

    记录按集群名关联，不会随配置一起删除。留着的话，同名集群换了命名空间重新配置后，
    新命名空间里还没有 CR，旧记录却会让模板显示为可用
    """
    E2BSandboxTemplateSyncRecord.objects.filter(cluster_name=cluster_name).delete()


def _record(template: E2BSandboxTemplate, cluster_name: str, status: E2BTemplateSyncStatus, message: str = "") -> None:
    """记录下发状态。下发完成（无论成败）时 template 须是刚下发的那份，摘要按它计算"""
    defaults: dict[str, Any] = {"status": status.value, "message": _truncate(message)}
    if status != E2BTemplateSyncStatus.PENDING:
        defaults["digest"] = spec_digest(template)
    E2BSandboxTemplateSyncRecord.objects.update_or_create(
        template=template, cluster_name=cluster_name, defaults=defaults
    )


def _delete_non_target_records(template: E2BSandboxTemplate, target_names: set[str]) -> None:
    """删掉不再是目标的集群的记录，如已停用 e2b 的集群"""
    E2BSandboxTemplateSyncRecord.objects.filter(template=template).exclude(cluster_name__in=target_names).delete()


def _truncate(message: str) -> str:
    """失败原因入库、返回前截断，k8s 的报错可能带上整个响应体"""
    return message[:2000]


# 集群资源操作


def _apply(client: EnhancedApiClient, template: E2BSandboxTemplate, namespace: str) -> None:
    """创建或覆盖模板的 CR。先模板后池子，池子引用的模板必须先存在"""
    name = template.resource_name
    _kres(kres.KSandboxTemplate, client).create_or_update(
        name,
        namespace=namespace,
        body=build_template_manifest(template, namespace),
        update_method="replace",
        auto_add_version=True,
    )
    _kres(kres.KSandboxPool, client).create_or_update(
        name,
        namespace=namespace,
        body=build_pool_manifest(template, namespace),
        update_method="replace",
        auto_add_version=True,
    )


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
    """清理由平台管理、但数据库中已不存在的模板留下的 CR"""
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
