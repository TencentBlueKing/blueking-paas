# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, Type

from attrs import define
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext as _

from paasng.accessories.iam.permissions.perm import PermCtx, Permission
from paasng.accessories.iam.permissions.request import ResourceRequest


class Admin42Action(str, StructuredEnum):
    """蓝鲸 PaaS 后台管理相关权限"""

    # 平台管理（增强服务，运行时，应用集群，应用资源方案，应用管理，用户管理，代码库配置管理等）
    MANAGE_PLATFORM = EnumField('manage_platform', label=_('平台管理'))
    # 应用模板管理（场景/应用模板管理）
    MANAGE_APP_TEMPLATES = EnumField('manage_app_templates', label=_('应用模板管理'))
    # 平台运营（查看平台运营数据）
    OPERATE_PLATFORM = EnumField('operate_platform', label=_('平台运营'))


@define
class Admin42PermCtx(PermCtx):
    pass


@define
class Admin42Request(ResourceRequest):
    @classmethod
    def from_dict(cls, init_data: Dict) -> 'Admin42Request':
        return cls()


class Admin42Permission(Permission):
    """后台管理权限"""

    resource_request_cls: Type[ResourceRequest] = Admin42Request

    def can_manage_platform(self, perm_ctx: Admin42PermCtx, raise_exception: bool = True) -> bool:
        return self.can_action(perm_ctx, Admin42Action.MANAGE_PLATFORM, raise_exception)

    def can_manage_app_templates(self, perm_ctx: Admin42PermCtx, raise_exception: bool = True) -> bool:
        return self.can_action(perm_ctx, Admin42Action.MANAGE_APP_TEMPLATES, raise_exception)

    def can_operate_platform(self, perm_ctx: Admin42PermCtx, raise_exception: bool = True) -> bool:
        return self.can_action(perm_ctx, Admin42Action.OPERATE_PLATFORM, raise_exception)
