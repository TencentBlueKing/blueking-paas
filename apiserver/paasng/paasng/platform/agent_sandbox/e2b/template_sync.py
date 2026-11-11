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

"""把平台的 e2b 沙箱模板以 CR 形式下发到启用了 e2b 的集群。

数据库是唯一的事实来源：每个模板对应集群里同名的一个 SandboxTemplate 与一个 SandboxPool，
网关把资源名当作 e2b 的 templateID。下发是幂等的 upsert，失败的集群只记录结果、不回滚，
由平台管理端的手动同步补齐。

平台下发的 CR 都带 managed-by 标签。删除与清理只动带标签的 CR，集群里手工创建的不受影响。

下发成功时，记录上留下所下发配置的摘要。创建沙箱前比对选中集群上的摘要与模板当前配置，
不一致就拒绝，以免用户改完模板后拿到的还是旧配置的沙箱。内置模板已预热的实例不在此列，
池子不跟随模板变化，它们保持旧配置直到被消耗完。

全量同步与单模板同步共用一把全局锁，拿到锁之后才读库，因此最后执行的一方用的总是最新状态。
锁只串行化向集群的下发，模板的增删改只写库、投递任务，不受影响。代价是下发排队：
单模板下发只需秒级，撞上时多等一轮重试；全量同步期间保存的模板，要等它结束才下发。
模板保存频率低，不值得为此按模板拆锁。
"""

import hashlib
import json
import logging
import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import (
    SANDBOX_INSTANCE_API_VERSION,
    SANDBOX_INSTANCE_DESIRED_STATE_RUNNING,
    SANDBOX_INSTANCE_NETWORK_MODE,
    SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
)
from paas_wl.infras.cluster.models import ClusterE2BConfig
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.platform.applications.models import Application
from paasng.utils.lock import redis_lock

from .clusters import list_e2b_clusters, select_e2b_cluster
from .constants import (
    GATEWAY_TEMPLATE_LABEL,
    TEMPLATE_MANAGED_BY_LABEL,
    TEMPLATE_MANAGED_BY_VALUE,
    TEMPLATE_PVC_SIZE_RATIO,
    TEMPLATE_SYNC_LOCK_TIMEOUT_SECONDS,
    E2BTemplateStatus,
    E2BTemplateSyncStatus,
)
from .exceptions import E2BClusterUnavailable, E2BTemplateSyncInProgress

logger = logging.getLogger(__name__)

SYNC_LOCK_KEY = "lock:sync_e2b_templates"

# 决定沙箱规格的字段，即 SandboxTemplate 里来自模板的部分
SPEC_DIGEST_FIELDS = ("image", "cpu_count", "memory_mb", "disk_size_mb", "env_vars", "workdir")


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


def build_template_manifest(template: E2BSandboxTemplate, namespace: str) -> dict[str, Any]:
    """生成模板对应的 SandboxTemplate"""
    name = template.resource_name
    container: dict[str, Any] = {"name": "main", "image": template.image, "imagePullPolicy": "IfNotPresent"}
    if template.env_vars:
        container["env"] = [{"name": k, "value": v} for k, v in sorted(template.env_vars.items())]
    if template.workdir:
        container["workingDir"] = template.workdir

    spec: dict[str, Any] = {
        "desiredState": SANDBOX_INSTANCE_DESIRED_STATE_RUNNING,
        "runtimeClassName": SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
        "network": {"mode": SANDBOX_INSTANCE_NETWORK_MODE},
        "domain": {"cpu": {"cores": template.cpu_count}, "memory": f"{template.memory_mb}Mi"},
        "podTemplate": {"containers": [container]},
        "retention": {"pod": "Delete", "pvc": "Delete", "dataVolume": "Delete"},
    }
    if template.disk_size_mb:
        _add_rootfs_disk(spec, template.disk_size_mb)

    return {
        "apiVersion": SANDBOX_INSTANCE_API_VERSION,
        "kind": "SandboxTemplate",
        "metadata": {"name": name, "namespace": namespace, "labels": _managed_labels()},
        "spec": {
            "template": {
                # 预热实例创建时就带上，网关据此回填 templateID
                "metadata": {"labels": {GATEWAY_TEMPLATE_LABEL: name}},
                "spec": spec,
            }
        },
    }


def _add_rootfs_disk(spec: dict[str, Any], disk_size_mb: int) -> None:
    """系统盘以盘镜像文件的形式放在每个沙箱独占的 PVC 上，PVC 要给文件系统开销留余量。

    布局与网关示例一致：盘镜像文件放在 PVC 的 rootfs 目录下
    """
    volume_name, pvc_name = "state", "state-pvc"
    pvc_size_mb = math.ceil(disk_size_mb * TEMPLATE_PVC_SIZE_RATIO)
    spec["domain"]["devices"] = {
        "disks": [
            {
                "name": "rootdisk",
                "role": "rootfsDisk",
                "volumeName": volume_name,
                "sourcePath": "rootfs",
                "image": "rootdisk.img",
                "fsType": "ext4",
                "size": f"{disk_size_mb}Mi",
            }
        ]
    }
    spec["podTemplate"]["volumes"] = [{"name": volume_name, "persistentVolumeClaim": {"claimName": pvc_name}}]
    spec["volumeClaimTemplates"] = [
        {
            "metadata": {"name": pvc_name},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": settings.AGENT_SANDBOX_E2B_TEMPLATE_STORAGE_CLASS,
                "resources": {"requests": {"storage": f"{pvc_size_mb}Mi"}},
            },
        }
    ]


def build_pool_manifest(template: E2BSandboxTemplate, namespace: str) -> dict[str, Any]:
    """生成模板对应的 SandboxPool。自定义模板不预热，靠网关在无库存时现场创建"""
    replicas = template.prewarm_count if template.is_builtin else 0
    return {
        "apiVersion": SANDBOX_INSTANCE_API_VERSION,
        "kind": "SandboxPool",
        "metadata": {"name": template.resource_name, "namespace": namespace, "labels": _managed_labels()},
        "spec": {"replicas": replicas, "templateRef": {"name": template.resource_name}},
    }


def spec_digest(template: E2BSandboxTemplate) -> str:
    """模板当前规格的摘要，与记录上的摘要相同即集群里的 SandboxTemplate 已是当前配置。

    只算模板字段，不算整份清单：平台生成清单的方式变了（标签、存储类等），集群里的旧 CR 照样能用，
    不该因此拦住所有创建。增删这里的字段会让全部记录对不上，上线后须做一次全量同步
    """
    spec = {f: getattr(template, f) for f in SPEC_DIGEST_FIELDS}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


@dataclass
class TemplateSyncOverview:
    """单个模板在各目标集群上的下发状态

    :param status: 汇总状态，任一集群失败即为失败，否则任一集群未完成即为待同步；没有目标集群时为空
    :param records: 各目标集群的下发记录
    :param missing: 是目标集群却没有记录的，多半是之后才启用 e2b、还没做过全量同步
    """

    template: E2BSandboxTemplate
    status: str | None
    records: list[E2BSandboxTemplateSyncRecord]
    missing: list[str]


@dataclass
class ClusterSyncOverview:
    """单个集群上各模板的下发状态，按资源名列出

    :param missing: 应当下发到该集群、却没有记录的模板
    """

    cluster_name: str
    namespace: str
    succeeded: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        """应当下发到该集群的模板是否全部同步成功"""
        return not (self.pending or self.failed or self.missing)


def mark_pending(template: E2BSandboxTemplate) -> None:
    """模板保存后、下发前调用：目标集群全部置为待同步，不再是目标的集群的记录删除"""
    target_names = _TargetResolver(_enabled_cluster_names()).resolve(template)
    _delete_non_target_records(template, target_names)
    for cluster_name in target_names:
        _record(template, cluster_name, E2BTemplateSyncStatus.PENDING)


def mark_sync_pending(cluster_names: set[str] | None = None, resource_names: set[str] | None = None) -> None:
    """投递同步任务前调用：范围内已有的记录置为待同步，概览里没有待同步即同步完成。参数同 ``sync_all``。

    没有记录的目标集群在概览里本就算未完成，不再是目标的集群不计入概览、由同步删除，
    所以只需改已有的记录，模板再多也是一条 SQL
    """
    records = E2BSandboxTemplateSyncRecord.objects.all()
    if cluster_names is not None:
        records = records.filter(cluster_name__in=cluster_names)
    if resource_names is not None:
        records = records.filter(template__resource_name__in=resource_names)
    records.update(status=E2BTemplateSyncStatus.PENDING.value, message="")


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
        for config in _enabled_configs():
            try:
                with get_client_by_cluster_name(config.cluster.name) as client:
                    _delete_managed(client, resource_name, config.namespace)
            except Exception:
                logger.exception(
                    "failed to delete e2b template %s from cluster %s", resource_name, config.cluster.name
                )
        return

    configs = _enabled_configs()
    # 目标集群可能在保存之后有变化，以下发时为准
    target_names = _TargetResolver({c.cluster.name for c in configs}).resolve(template)
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
    configs = _enabled_configs()
    # 目标集群按全部启用 e2b 的集群求，只限定下发范围，否则范围外集群的记录会被当成不再是目标而删掉
    resolver = _TargetResolver({c.cluster.name for c in configs})
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


def get_template_overviews(templates: list[E2BSandboxTemplate]) -> list[TemplateSyncOverview]:
    """按模板汇总下发状态。模板须已 select_related("application") 与 prefetch_related("sync_records")"""
    resolver = _TargetResolver(_enabled_cluster_names())

    overviews = []
    for template in templates:
        target_names = resolver.resolve(template)
        records = [r for r in template.sync_records.all() if r.cluster_name in target_names]
        missing = sorted(target_names - {r.cluster_name for r in records})
        overviews.append(
            TemplateSyncOverview(
                template=template,
                status=_summarize({r.status for r in records}, has_missing=bool(missing)),
                records=records,
                missing=missing,
            )
        )
    return overviews


def get_cluster_overviews() -> list[ClusterSyncOverview]:
    """按集群汇总各模板的下发状态，覆盖全部启用 e2b 的集群"""
    configs = _enabled_configs()
    overviews = {
        c.cluster.name: ClusterSyncOverview(cluster_name=c.cluster.name, namespace=c.namespace) for c in configs
    }
    resolver = _TargetResolver(set(overviews))

    for template in E2BSandboxTemplate.objects.select_related("application").prefetch_related("sync_records"):
        records = {r.cluster_name: r for r in template.sync_records.all()}
        for cluster_name in resolver.resolve(template):
            overview = overviews[cluster_name]
            record = records.get(cluster_name)
            if record is None:
                overview.missing.append(template.resource_name)
            elif record.status == E2BTemplateSyncStatus.SUCCEEDED.value:
                overview.succeeded.append(template.resource_name)
            elif record.status == E2BTemplateSyncStatus.FAILED.value:
                overview.failed[template.resource_name] = record.message
            else:
                overview.pending.append(template.resource_name)
    return list(overviews.values())


def is_applied(template: E2BSandboxTemplate, cluster_name: str) -> bool:
    """集群里的 SandboxTemplate 是否已是模板的当前配置"""
    record = E2BSandboxTemplateSyncRecord.objects.filter(template=template, cluster_name=cluster_name).first()
    return record is not None and record.applied_digest == spec_digest(template)


def get_template_statuses(
    application: Application, templates: Sequence[E2BSandboxTemplate]
) -> dict[str, E2BTemplateStatus]:
    """应用视角下各模板能否用来创建沙箱，键为资源名。

    按应用当前的首选集群判断，与创建沙箱时的检查一致。首选集群会随分配策略变化，
    所以只反映此刻的结果
    """
    try:
        cluster_name = select_e2b_cluster(application.tenant_id, application.region).name
    except E2BClusterUnavailable:
        return {t.resource_name: E2BTemplateStatus.NO_CLUSTER for t in templates}

    records = {
        r.template_id: r
        for r in E2BSandboxTemplateSyncRecord.objects.filter(template__in=templates, cluster_name=cluster_name)
    }
    return {t.resource_name: _template_status(t, records.get(t.pk)) for t in templates}


def _template_status(template: E2BSandboxTemplate, record: E2BSandboxTemplateSyncRecord | None) -> E2BTemplateStatus:
    # 已是当前配置就可用，不看 status：运维重新同步时会先置为待同步，失败了集群里的 CR 也还在
    if record is not None and record.applied_digest == spec_digest(template):
        return E2BTemplateStatus.AVAILABLE
    if record is not None and record.status == E2BTemplateSyncStatus.FAILED.value:
        return E2BTemplateStatus.SYNC_FAILED
    return E2BTemplateStatus.SYNCING


def _enabled_configs() -> list[ClusterE2BConfig]:
    return list(ClusterE2BConfig.objects.select_related("cluster").filter(enabled=True))


def _enabled_cluster_names() -> set[str]:
    return set(ClusterE2BConfig.objects.filter(enabled=True).values_list("cluster__name", flat=True))


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


class _TargetResolver:
    """求模板应当下发到的集群：内置模板是全部启用 e2b 的集群，自定义模板只到应用租户可分配的那些。

    自定义模板的目标集群要走一遍集群分配，同一（租户, region）下的结果相同，实例内按此缓存，
    批量处理模板时复用同一个实例即可。

    :param enabled_names: 启用 e2b 的集群名
    """

    def __init__(self, enabled_e2b_clusters: set[str]):
        self._enabled_e2b_clusters = enabled_e2b_clusters
        self._allocated: dict[tuple[str, str], set[str]] = {}

    def resolve(self, template: E2BSandboxTemplate) -> set[str]:
        if template.is_builtin:
            return self._enabled_e2b_clusters

        app = template.application
        key = (app.tenant_id, app.region)
        if key not in self._allocated:
            try:
                names = set(list_e2b_clusters(app.tenant_id, app.region).values_list("name", flat=True))
            except E2BClusterUnavailable:
                logger.warning("no e2b cluster allocated for tenant %s, skip its custom templates", app.tenant_id)
                names = set()
            self._allocated[key] = names
        return self._allocated[key] & self._enabled_e2b_clusters


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
        if not _is_managed(obj.to_dict()):
            logger.warning(
                "%s %s/%s is not managed by platform, skip deleting", kres_cls.kind, namespace, resource_name
            )
            continue
        res.delete(resource_name, namespace=namespace)
        deleted = True
    return deleted


def _prune(client: EnhancedApiClient, namespace: str, known_resource_names: set[str]) -> list[str]:
    """清理由平台管理、但数据库中已不存在的模板留下的 CR"""
    selector = _managed_labels()
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


def _record(template: E2BSandboxTemplate, cluster_name: str, status: E2BTemplateSyncStatus, message: str = "") -> None:
    """记录下发结果。成功时 template 须是刚下发的那份，摘要按它计算"""
    defaults: dict[str, Any] = {"status": status.value, "message": _truncate(message)}
    if status == E2BTemplateSyncStatus.SUCCEEDED:
        defaults["applied_digest"] = spec_digest(template)
    E2BSandboxTemplateSyncRecord.objects.update_or_create(
        template=template, cluster_name=cluster_name, defaults=defaults
    )


def _delete_non_target_records(template: E2BSandboxTemplate, target_names: set[str]) -> None:
    """删掉不再是目标的集群的记录，如已停用 e2b 的集群"""
    E2BSandboxTemplateSyncRecord.objects.filter(template=template).exclude(cluster_name__in=target_names).delete()


def _summarize(statuses: set[str], has_missing: bool) -> str | None:
    if E2BTemplateSyncStatus.FAILED.value in statuses:
        return E2BTemplateSyncStatus.FAILED.value
    if has_missing or E2BTemplateSyncStatus.PENDING.value in statuses:
        return E2BTemplateSyncStatus.PENDING.value
    if statuses:
        return E2BTemplateSyncStatus.SUCCEEDED.value
    return None


def _kres(kres_cls: type[kres.BaseKresource], client: EnhancedApiClient) -> kres.BaseKresource:
    return kres_cls(client, api_version=SANDBOX_INSTANCE_API_VERSION)


def _managed_labels() -> dict[str, str]:
    return {TEMPLATE_MANAGED_BY_LABEL: TEMPLATE_MANAGED_BY_VALUE}


def _is_managed(manifest: dict[str, Any]) -> bool:
    labels = manifest.get("metadata", {}).get("labels") or {}
    return labels.get(TEMPLATE_MANAGED_BY_LABEL) == TEMPLATE_MANAGED_BY_VALUE


def _truncate(message: str) -> str:
    """失败原因入库、返回前截断，k8s 的报错可能带上整个响应体"""
    return message[:2000]
