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

"""根据下发记录汇总模板的下发状态，判断模板能否用来创建沙箱。只读，不改记录、不连集群。

每个集群的下发记录只描述最近一次下发：结果，以及所下发配置的摘要。创建沙箱前要求选中集群上
最近一次下发成功、且摘要与模板当前配置一致，以免用户改完模板后拿到的还是旧配置的沙箱。
下发失败就不可用：模板与池子分两步写入，失败时集群里可能已是新旧混合的状态。内置模板已预热的
实例不在此列，池子不跟随模板变化，它们保持旧配置直到被消耗完。
"""

from dataclasses import dataclass, field
from typing import Sequence

from paasng.platform.agent_sandbox.e2b.clusters import (
    TemplateTargetResolver,
    list_enabled_e2b_cluster_names,
    list_enabled_e2b_configs,
    select_e2b_cluster,
)
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateStatus, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BClusterUnavailable
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord
from paasng.platform.applications.models import Application

from .manifests import spec_digest


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


def get_template_overviews(templates: list[E2BSandboxTemplate]) -> list[TemplateSyncOverview]:
    """按模板汇总下发状态。模板须已 select_related("application") 与 prefetch_related("sync_records")"""
    resolver = TemplateTargetResolver(list_enabled_e2b_cluster_names())

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
    overviews = {
        c.cluster.name: ClusterSyncOverview(cluster_name=c.cluster.name, namespace=c.namespace)
        for c in list_enabled_e2b_configs()
    }
    resolver = TemplateTargetResolver(set(overviews))

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
    return record is not None and is_current(record, template)


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


def is_current(record: E2BSandboxTemplateSyncRecord, template: E2BSandboxTemplate) -> bool:
    """最近一次下发成功，且下发的就是模板当前配置"""
    return record.status == E2BTemplateSyncStatus.SUCCEEDED.value and record.digest == spec_digest(template)


def _template_status(template: E2BSandboxTemplate, record: E2BSandboxTemplateSyncRecord | None) -> E2BTemplateStatus:
    if record is None:
        return E2BTemplateStatus.SYNCING
    if is_current(record, template):
        return E2BTemplateStatus.AVAILABLE
    if record.status == E2BTemplateSyncStatus.FAILED.value:
        return E2BTemplateStatus.SYNC_FAILED
    return E2BTemplateStatus.SYNCING


def _summarize(statuses: set[str], has_missing: bool) -> str | None:
    if E2BTemplateSyncStatus.FAILED.value in statuses:
        return E2BTemplateSyncStatus.FAILED.value
    if has_missing or E2BTemplateSyncStatus.PENDING.value in statuses:
        return E2BTemplateSyncStatus.PENDING.value
    if statuses:
        return E2BTemplateSyncStatus.SUCCEEDED.value
    return None
