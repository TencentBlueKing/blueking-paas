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

"""把 MySQL 环境绑定上的 plan 改成目标方案。已开通的环境要等实例 plan 已经切过去。"""

from dataclasses import dataclass

from paasng.accessories.servicehub.exceptions import SvcAttachmentDoesNotExist
from paasng.accessories.servicehub.remote.client import RemoteServiceClient
from paasng.accessories.servicehub.remote.exceptions import RemoteClientError
from paasng.accessories.servicehub.remote.manager import RemoteServiceMgr
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.platform.applications.models import Application


@dataclass
class AlignOutcome:
    updated: list[str]
    skipped: list[str]


def align_mysql_plans(
    app_code: str,
    target_plan_name: str,
    modules: list[str] | None,
    environments: list[str] | None,
) -> AlignOutcome:
    application = Application.objects.get(code=app_code)
    module_qs = application.modules.all()
    if modules:
        module_qs = module_qs.filter(name__in=modules)
        found = set(module_qs.values_list("name", flat=True))
        missing = [name for name in modules if name not in found]
        if missing:
            raise LookupError(f"这些模块不存在: {', '.join(missing)}")

    store = get_remote_store()
    manager = RemoteServiceMgr(store)
    services = manager.get_mysql_services()
    if not services:
        raise LookupError("找不到 MySQL 增强服务")

    updated: list[str] = []
    skipped: list[str] = []
    bound = False
    for service in services:
        target_plan = _plan_by_name(service, target_plan_name)
        client = RemoteServiceClient(store.get_source_config(str(service.uuid)))
        for module in module_qs:
            for env in module.envs.all():
                if environments and env.environment not in environments:
                    continue
                try:
                    attachment = manager.get_attachment_by_engine_app(service, env.engine_app)
                except SvcAttachmentDoesNotExist:
                    continue
                bound = True
                label = f"{app_code}/{module.name}/{env.environment}"
                if target_plan is None:
                    skipped.append(f"{label} 的服务 {service.name} 没有名为 {target_plan_name} 的 plan")
                    continue
                instance_plan_id = _read_instance_plan(client, attachment)
                if instance_plan_id is _MISSING:
                    skipped.append(f"{label} 读取实例失败，绑定未改")
                    continue
                message, did_update = align_binding(attachment, target_plan.uuid, instance_plan_id, label)
                (updated if did_update else skipped).append(message)

    if not bound:
        raise LookupError(f"应用 {app_code} 在指定范围内没有 MySQL 绑定")
    return AlignOutcome(updated=updated, skipped=skipped)


# retrieve 失败和「还没开通」都不是一个 plan id，分开表示。
_MISSING = object()


def align_binding(attachment, target_plan_id: str, instance_plan_id: str | None, label: str) -> tuple[str, bool]:
    """instance_plan_id 为 None 表示还没开通。返回 (说明, 是否已更新)。"""
    if _same_id(attachment.plan_id, target_plan_id):
        return f"{label} 绑定已经是目标 plan", False
    # 已开通但实例仍是源 plan 时不改。改早了，下次部署幂等开通会返回 400。
    if attachment.service_instance_id and not _same_id(instance_plan_id, target_plan_id):
        return (
            f"{label} 实例仍不是目标 plan。请先在 svc-mysql 执行 migrate_plan switch，成功后再运行本命令",
            False,
        )

    attachment.plan_id = target_plan_id
    attachment.save(update_fields=["plan_id"])
    if attachment.service_instance_id:
        return f"{label} 实例已经在目标 plan，绑定已对齐。请重新部署应用", True
    return f"{label} 尚未开通，绑定已改为目标 plan。下次部署会按这个 plan 开通", True


def _read_instance_plan(client, attachment):
    if not attachment.service_instance_id:
        return None
    try:
        return client.retrieve_instance(str(attachment.service_instance_id)).get("plan")
    except RemoteClientError:
        return _MISSING


def _plan_by_name(service, name: str):
    matched = [plan for plan in service.get_plans() if plan.name == name]
    if not matched:
        return None
    if len(matched) > 1:
        raise LookupError(f"服务 {service.name} 的 plan 名称 {name} 对应多条记录，本命令只支持单租户")
    return matched[0]


def _same_id(left, right) -> bool:
    if left is None or right is None:
        return False
    return str(left).replace("-", "").lower() == str(right).replace("-", "").lower()
