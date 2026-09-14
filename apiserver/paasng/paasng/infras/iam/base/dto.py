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

from typing import Any, Dict, List, Optional

from attrs import define, field


@define
class AuthResource:
    """鉴权请求中的资源实例

    V3 实现将其转换为 SDK 的 `iam.Resource`，V4 实现将其序列化为 HTTP 请求体中的
    资源描述，调用方不感知两者的差异。
    """

    system: str
    type: str
    id: str
    attribute: Dict[str, Any] = field(factory=dict)


@define
class ActionRequest:
    """申请链接中的一项操作及其关联的资源实例

    :param resource_ids: 资源实例 ID 列表。为空表示该操作与资源实例无关；
        非空时各实例必须具有相同的父实例
    """

    action_id: str
    resource_type: Optional[str] = None
    resource_ids: List[str] = field(factory=list)


@define
class ManagementSpace:
    """管理空间

    V3 语义为分级管理员，V4 语义为管理空间。两个版本的 ID 均为整型。
    """

    id: int
    name: str
    description: str = ""


@define
class UserGroup:
    """应用/插件的内建用户组

    :param role: 用户组对应的角色值，应用侧取 `ApplicationRole`，插件侧取 `PluginRole`
    """

    id: int
    name: str
    role: int
    description: str = ""


@define
class GroupMember:
    """用户组成员

    :param expired_at: 权限到期时间戳。V3 支持传入远期时间实现「永不过期」；
        V4 的有效期由用户组统一约束，当前上限为一年，详见 `#6` 子需求说明。
    """

    username: str
    expired_at: Optional[int] = None


@define
class AuthorizationScope:
    """用户组或管理空间的授权范围

    结构与权限中心的 `authorization_scopes` 一致，由各版本实现自行组装。
    因 V3 与 V4 的操作模型差异较大（V4 不再提供 `related_actions`），
    此处仅承载已组装好的载荷，不做跨版本的结构抽象。
    """

    system: str
    actions: List[Dict[str, Any]]
    resources: List[Dict[str, Any]] = field(factory=list)

    def to_data(self) -> Dict[str, Any]:
        return {"system": self.system, "actions": self.actions, "resources": self.resources}
