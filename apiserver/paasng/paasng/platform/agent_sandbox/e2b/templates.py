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

"""e2b 沙箱模板的维护：命名、增删改，以及触发向集群的下发。

用户只接触模板标识（SDK 传入的 templateID），集群里的资源名由平台生成：
内置模板的资源名与模板标识相同，自定义模板的资源名带上应用前缀。所有集群共用一个命名空间，
加前缀才能让不同应用的同名模板互不干扰。
"""

from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction

from paasng.platform.agent_sandbox.models import E2BSandbox, E2BSandboxTemplate
from paasng.platform.applications.models import Application

from .constants import CUSTOM_RESOURCE_NAME_SEPARATOR, RESOURCE_NAME_MAX_LENGTH, E2BSandboxStatus
from .exceptions import (
    E2BTemplateAlreadyExists,
    E2BTemplateIDTooLong,
    E2BTemplateInUse,
    E2BTemplateQuotaExceeded,
)
from .tasks import sync_e2b_template_task
from .template_sync import MANIFEST_FIELDS, mark_pending

# 创建后可修改的字段，模板标识决定了资源名，不能改
COMMON_MUTABLE_FIELDS = (
    "name",
    "description",
    "image",
    "cpu_count",
    "memory_mb",
    "disk_size_mb",
    "env_vars",
    "workdir",
)
BUILTIN_MUTABLE_FIELDS = (*COMMON_MUTABLE_FIELDS, "prewarm_count", "enabled", "is_public")


def get_custom_resource_prefix(application: Application) -> str:
    """自定义模板资源名的应用前缀。S-mart 应用的 code 允许下划线，k8s 资源名不接受，按平台惯例转义"""
    return application.code.lower().replace("_", "0us0") + CUSTOM_RESOURCE_NAME_SEPARATOR


def make_custom_resource_name(application: Application, template_id: str) -> str:
    return get_custom_resource_prefix(application) + template_id


def to_sdk_template_id(application: Application, resource_name: str) -> str:
    """把网关返回的资源名还原成用户使用的模板标识。内置模板的资源名不带前缀，原样返回"""
    prefix = get_custom_resource_prefix(application)
    if resource_name.startswith(prefix):
        return resource_name[len(prefix) :]
    return resource_name


def create_builtin_template(template_id: str, **spec: Any) -> E2BSandboxTemplate:
    """创建内置模板。

    :raises E2BTemplateAlreadyExists: 已有同名的内置模板，或已有应用用这个标识建了自定义模板
    """
    if E2BSandboxTemplate.objects.filter(template_id=template_id).exists():
        raise E2BTemplateAlreadyExists(f"template {template_id} already exists")

    return _create(
        template_id=template_id,
        resource_name=template_id,
        **spec,
    )


def create_custom_template(application: Application, template_id: str, **spec: Any) -> E2BSandboxTemplate:
    """为应用创建自定义模板，固定启用、不预热。

    :raises E2BTemplateIDTooLong: 加上应用前缀后资源名超长，应用 code 较长时可用的模板标识会更短
    :raises E2BTemplateQuotaExceeded: 应用的自定义模板数量已达上限
    :raises E2BTemplateAlreadyExists: 应用下已有同名模板，或与内置模板重名
    """
    resource_name = make_custom_resource_name(application, template_id)
    if len(resource_name) > RESOURCE_NAME_MAX_LENGTH:
        max_length = RESOURCE_NAME_MAX_LENGTH - len(get_custom_resource_prefix(application))
        raise E2BTemplateIDTooLong(f"template id of app {application.code} must be at most {max_length} characters")

    custom = E2BSandboxTemplate.objects.custom_of(application)
    if custom.count() >= settings.AGENT_SANDBOX_E2B_MAX_CUSTOM_TEMPLATES_PER_APP:
        raise E2BTemplateQuotaExceeded(f"app {application.code} has too many custom templates")
    # 不公开的内置模板也算：任意应用都能按标识用它，重名就分不清 SDK 要的是哪个
    if (
        custom.filter(template_id=template_id).exists()
        or E2BSandboxTemplate.objects.builtins().filter(template_id=template_id).exists()
    ):
        raise E2BTemplateAlreadyExists(f"template {template_id} already exists")

    spec.pop("prewarm_count", None)
    return _create(
        application=application,
        template_id=template_id,
        resource_name=resource_name,
        tenant_id=application.tenant_id,
        **spec,
    )


def update_template(template: E2BSandboxTemplate, **changes: Any) -> list[str]:
    """修改模板，改到 CR 里的字段时重新下发。网关的池子不跟随模板变化，已预热的实例保持旧配置，直到被消耗完。

    :returns: 实际发生变化的字段
    """
    allowed = BUILTIN_MUTABLE_FIELDS if template.is_builtin else COMMON_MUTABLE_FIELDS
    changed = [f for f, v in changes.items() if f in allowed and getattr(template, f) != v]
    if not changed:
        return []

    for f in changed:
        setattr(template, f, changes[f])
    with transaction.atomic():
        template.save(update_fields=[*changed, "updated"])
        if set(changed) & set(MANIFEST_FIELDS):
            _schedule_sync(template)
    return changed


def delete_template(template: E2BSandboxTemplate, force: bool = False) -> None:
    """删除模板，并从集群中删除它的 CR。

    :param force: 不检查是否还有未终止的沙箱，应用删除时使用
    :raises E2BTemplateInUse: 模板下还有未终止的沙箱。删除池子会连带销毁它们
    """
    if not force and has_active_sandboxes(template):
        raise E2BTemplateInUse(f"template {template.resource_name} still has active sandboxes")

    with transaction.atomic():
        template.delete()
        _schedule_cleanup(template.resource_name)


def delete_custom_templates_of(application: Application) -> None:
    """应用删除时，一并删除它的自定义模板。沙箱随应用一起作废，不再检查"""
    for template in E2BSandboxTemplate.objects.custom_of(application):
        delete_template(template, force=True)


def has_active_sandboxes(template: E2BSandboxTemplate) -> bool:
    return E2BSandbox.objects.filter(
        template_id=template.resource_name, status__in=E2BSandboxStatus.active_values()
    ).exists()


def _create(**fields: Any) -> E2BSandboxTemplate:
    try:
        with transaction.atomic():
            template = E2BSandboxTemplate.objects.create(**fields)
            _schedule_sync(template)
    except IntegrityError as exc:
        # 并发创建同名模板时，资源名的唯一约束兜底
        raise E2BTemplateAlreadyExists(f"template {fields['resource_name']} already exists") from exc
    return template


def _schedule_sync(template: E2BSandboxTemplate) -> None:
    """目标集群先记为待同步，事务提交后再下发，任务读到的才是已落库的状态"""
    mark_pending(template)
    resource_name = template.resource_name
    transaction.on_commit(lambda: sync_e2b_template_task.delay(resource_name))


def _schedule_cleanup(resource_name: str) -> None:
    """模板删除后，从集群中删除它的 CR。下发记录随模板一起删除"""
    transaction.on_commit(lambda: sync_e2b_template_task.delay(resource_name))
