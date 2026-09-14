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

"""两个系统在 IAM V4 上的本地模型定义

从现有枚举与角色映射抽取系统、资源类型、操作、角色四类数据，丢弃 V4 无对应物的
action_groups / common_actions / resource_creator_actions / related_actions。
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence
from urllib.parse import urljoin

from attrs import define, field
from django.conf import settings
from django.utils.encoding import force_str

from paasng.infras.iam.constants import ResourceType
from paasng.infras.iam.exceptions import InvalidIAMIdentifierError
from paasng.infras.iam.permissions.resources.application import AppAction, AppRole
from paasng.infras.iam.permissions.resources.plugin import PluginIAMRole, PluginPermissionActions
from paasng.infras.iam.shim import get_paas_system_id, get_plugin_system_id

# 小写字母开头，只含小写字母/数字/下划线/连字符，最长 32 字符
V4_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")

PAAS_RESOURCE_TYPE_ID = ResourceType.Application.value
PLUGIN_RESOURCE_TYPE_ID = "plugin"

PAAS_CALLBACK_PATH = "/backend/api/iam-provider/applications/"
PLUGIN_CALLBACK_PATH = "/backend/api/bkplugins/shim/iam/selection/plugin_view/"

SYSTEM_ALIAS_PAAS = "paas"
SYSTEM_ALIAS_PLUGINS = "plugins"


@define(frozen=True)
class ResourceTypeDefinition:
    id: str
    name: str
    ancestors: List[str] = field(factory=list)

    def to_create_payload(self) -> Dict:
        return {"id": self.id, "name": self.name, "ancestors": list(self.ancestors)}

    def to_update_payload(self) -> Dict:
        return {"name": self.name, "ancestors": list(self.ancestors)}

    def differs_from(self, remote: Dict) -> bool:
        return self.name != remote.get("name") or list(self.ancestors) != list(remote.get("ancestors") or [])


@define(frozen=True)
class ActionDefinition:
    id: str
    name: str
    resource_type_id: str

    def to_create_payload(self) -> Dict:
        return {"id": self.id, "name": self.name, "resource_type_id": self.resource_type_id}

    def to_update_payload(self) -> Dict:
        # V4 更新操作只允许改名称，resource_type_id 创建后不可变
        return {"name": self.name}

    def differs_from(self, remote: Dict) -> bool:
        return self.name != remote.get("name")


@define(frozen=True)
class RoleActionDefinition:
    id: str
    resource_type_id: str

    def to_payload(self) -> Dict:
        return {"id": self.id, "resource_type_id": self.resource_type_id}

    def identity(self) -> tuple:
        return self.id, self.resource_type_id or ""


@define(frozen=True)
class RoleDefinition:
    id: str
    name: str
    description: str
    actions: List[RoleActionDefinition] = field(factory=list)

    def to_create_payload(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [action.to_payload() for action in self.actions],
        }

    def to_update_payload(self) -> Dict:
        return {"name": self.name, "description": self.description}

    def meta_differs_from(self, remote: Dict) -> bool:
        return self.name != remote.get("name") or self.description != (remote.get("description") or "")

    def local_action_ids(self) -> set:
        return {action.identity() for action in self.actions}

    def remote_action_ids(self, remote: Dict) -> set:
        return {(item.get("id"), item.get("resource_type_id") or "") for item in (remote.get("actions") or [])}


@define(frozen=True)
class SystemDefinition:
    id: str
    name: str
    description: str
    clients: List[str]
    callback_url: str
    resource_types: List[ResourceTypeDefinition]
    actions: List[ActionDefinition]
    roles: List[RoleDefinition]
    managers: List[str] = field(factory=list)

    def to_create_payload(self) -> Dict:
        payload = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "clients": list(self.clients),
            "callback_url": self.callback_url,
        }
        if self.managers:
            payload["managers"] = list(self.managers)
        return payload

    def to_update_payload(self) -> Dict:
        payload = {
            "name": self.name,
            "description": self.description,
            "clients": list(self.clients),
            "callback_url": self.callback_url,
        }
        if self.managers:
            payload["managers"] = list(self.managers)
        return payload

    def differs_from(self, remote: Dict) -> bool:
        return (
            self.name != remote.get("name")
            or self.description != (remote.get("description") or "")
            or set(self.clients) != set(remote.get("clients") or [])
            or self.callback_url != (remote.get("callback_url") or "")
        )

    def collect_identifiers(self) -> List[str]:
        identifiers = [self.id]
        identifiers.extend(item.id for item in self.resource_types)
        identifiers.extend(item.id for item in self.actions)
        identifiers.extend(item.id for item in self.roles)
        return identifiers


def is_valid_v4_identifier(value: str) -> bool:
    return bool(value) and V4_IDENTIFIER_RE.fullmatch(value) is not None


def validate_identifiers(definitions: Sequence[SystemDefinition]):
    """同步前校验"""
    invalid = [
        identifier
        for definition in definitions
        for identifier in definition.collect_identifiers()
        if not is_valid_v4_identifier(identifier)
    ]
    if invalid:
        raise InvalidIAMIdentifierError(invalid)


def _callback_url(path: str) -> str:
    host = (settings.BK_IAM_RESOURCE_API_HOST or "").rstrip("/") + "/"
    return urljoin(host, path.lstrip("/"))


def build_paas_system_definition() -> SystemDefinition:
    resource_type_id = PAAS_RESOURCE_TYPE_ID
    actions = [
        ActionDefinition(
            id=str(action),
            name=force_str(AppAction.get_choice_label(action)),
            resource_type_id=resource_type_id,
        )
        for action in AppAction
    ]
    roles = [
        RoleDefinition(
            id=str(role),
            name=force_str(AppRole.get_choice_label(role)),
            description=AppRole.get_description(role),
            actions=[
                RoleActionDefinition(id=str(action), resource_type_id=resource_type_id)
                for action in AppRole.get_actions(role)
            ],
        )
        for role in AppRole
    ]
    return SystemDefinition(
        id=get_paas_system_id(),
        name="开发者中心",
        description="蓝鲸开发者中心是一个开放式的 PaaS 平台，让开发者可以方便快捷地创建、开发、部署和管理 SaaS 应用。",
        clients=[settings.IAM_APP_CODE],
        callback_url=_callback_url(PAAS_CALLBACK_PATH),
        resource_types=[ResourceTypeDefinition(id=resource_type_id, name="应用")],
        actions=actions,
        roles=roles,
    )


def build_plugin_system_definition() -> SystemDefinition:
    resource_type_id = PLUGIN_RESOURCE_TYPE_ID
    actions = [
        ActionDefinition(
            id=str(action),
            name=force_str(PluginPermissionActions.get_choice_label(action)),
            resource_type_id=resource_type_id,
        )
        for action in PluginPermissionActions
    ]
    roles = [
        RoleDefinition(
            id=str(role),
            name=force_str(PluginIAMRole.get_choice_label(role)),
            description=PluginIAMRole.get_description(role),
            actions=[
                RoleActionDefinition(id=str(action), resource_type_id=resource_type_id)
                for action in PluginIAMRole.get_actions(role)
            ],
        )
        for role in PluginIAMRole
    ]
    return SystemDefinition(
        id=get_plugin_system_id(),
        name="插件开发者中心",
        description="蓝鲸插件开发者中心，提供插件的开发、发布与管理能力。",
        clients=[settings.IAM_APP_CODE],
        callback_url=_callback_url(PLUGIN_CALLBACK_PATH),
        resource_types=[ResourceTypeDefinition(id=resource_type_id, name="插件")],
        actions=actions,
        roles=roles,
    )


def iter_system_definitions() -> List[SystemDefinition]:
    return [build_paas_system_definition(), build_plugin_system_definition()]


def resolve_system_definitions(system_aliases: Iterable[str] | None) -> List[SystemDefinition]:
    """按命令行别名或系统 ID 解析要同步的系统，未指定则全量"""
    mapping = {
        SYSTEM_ALIAS_PAAS: build_paas_system_definition,
        SYSTEM_ALIAS_PLUGINS: build_plugin_system_definition,
        get_paas_system_id(): build_paas_system_definition,
        get_plugin_system_id(): build_plugin_system_definition,
    }
    if not system_aliases:
        return iter_system_definitions()

    selected: List[SystemDefinition] = []
    seen = set()
    unknown = []
    for alias in system_aliases:
        builder = mapping.get(alias)
        if builder is None:
            unknown.append(alias)
            continue
        definition = builder()
        if definition.id in seen:
            continue
        seen.add(definition.id)
        selected.append(definition)

    if unknown:
        raise ValueError(f"未知的系统: {', '.join(unknown)}，可选值为 {sorted(set(mapping))}")
    return selected
