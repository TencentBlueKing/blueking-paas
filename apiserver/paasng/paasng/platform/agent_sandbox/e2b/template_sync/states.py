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

"""维护各模板在各集群上的下发状态。

除下发本身外，模板保存、投递同步任务、集群下线时也要改状态，写状态的入口都在这里，读状态见 ``status``。
"""

from typing import Any

from paasng.platform.agent_sandbox.e2b.clusters import resolve_template_targets
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncState

from .manifests import spec_digest
from .status import is_up_to_date


def mark_pending(template: E2BSandboxTemplate) -> None:
    """模板保存后、下发前调用：目标集群全部置为待同步"""
    for cluster_name in resolve_template_targets([template])[template.resource_name]:
        save_sync_state(template, cluster_name, E2BTemplateSyncStatus.PENDING)


def reset_unsynced_to_pending(cluster_names: set[str] | None = None, resource_names: set[str] | None = None) -> None:
    """手动触发异步同步前调用：将范围内尚未同步到当前配置的已有记录（上次失败或配置落后）重置为待同步并清空报错。

    - Q: 为什么要重置
      A: 手动同步是异步执行的，若不清掉旧的失败结果，调用方刷新时无法区分「任务还没跑」和「重试后仍然失败」。
    - Q: 为什么跳过已同步记录
      A: 已是当前配置的 ``succeeded`` 记录保持不变，避免重同步期间模板短暂不可用（真失败了再由任务改为失败）。
    - Q: 为什么只改已有记录
      A: 尚无记录的新集群在概览中本就显示为 ``missing``，无需提前建记录；已下线集群的旧记录不计入概览，由同步收尾清理。
    """
    states = E2BSandboxTemplateSyncState.objects.select_related("template")
    if cluster_names is not None:
        states = states.filter(cluster_name__in=cluster_names)
    if resource_names is not None:
        states = states.filter(template__resource_name__in=resource_names)
    unsynced_pks = [s.pk for s in states if not is_up_to_date(s, s.template)]
    E2BSandboxTemplateSyncState.objects.filter(pk__in=unsynced_pks).update(
        status=E2BTemplateSyncStatus.PENDING.value, message=""
    )


def delete_cluster_sync_states(cluster_name: str) -> None:
    """删掉该集群的全部下发状态。

    状态按集群名关联，不会随配置一起删除。留着的话，同名集群换了命名空间重新配置后，
    新命名空间里还没有 CR，旧状态却会让模板显示为可用
    """
    E2BSandboxTemplateSyncState.objects.filter(cluster_name=cluster_name).delete()


def save_sync_state(
    template: E2BSandboxTemplate, cluster_name: str, status: E2BTemplateSyncStatus, message: str = ""
) -> None:
    """写入下发状态。下发完成（无论成败）时 template 须是刚下发的那份，摘要按它计算"""
    defaults: dict[str, Any] = {"status": status.value, "message": truncate_message(message)}
    if status != E2BTemplateSyncStatus.PENDING:
        defaults["digest"] = spec_digest(template)
    E2BSandboxTemplateSyncState.objects.update_or_create(
        template=template, cluster_name=cluster_name, defaults=defaults
    )


def prune_sync_states(templates: list[E2BSandboxTemplate], targets: dict[str, set[str]]) -> None:
    """同步收尾时清理用不上的状态：模板在不再是目标的集群（如已停用 e2b）上的，以及模板已不存在的。

    读状态的地方都只看目标集群，留着不影响结果，清理只为不让数据越积越多

    :param targets: 资源名到目标集群的映射，须按全部启用 e2b 的集群求出
    """
    for template in templates:
        E2BSandboxTemplateSyncState.objects.filter(template=template).exclude(
            cluster_name__in=targets[template.resource_name]
        ).delete()
    # 模板删除时状态会级联删除，这里兜底绕过 ORM 删掉的
    E2BSandboxTemplateSyncState.objects.exclude(template_id__in=E2BSandboxTemplate.objects.values("pk")).delete()


def truncate_message(message: str) -> str:
    """失败原因入库、返回前截断，k8s 的报错可能带上整个响应体"""
    return message[:2000]
