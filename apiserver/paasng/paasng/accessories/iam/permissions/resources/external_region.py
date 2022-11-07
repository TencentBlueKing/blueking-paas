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


class ExternalRegionAction(str, StructuredEnum):
    """蓝鲸 PaaS 外部版应用相关权限"""

    # 外部版应用创建
    CREATE_EXTERNAL_REGION_APP = EnumField('create_external_region_app', label=_('外部版应用创建'))
    # 外部版模块创建
    CREATE_EXTERNAL_REGION_MODULE = EnumField('create_external_region_module', label=_('外部版模块创建'))


@define
class ExternalRegionPermCtx(PermCtx):
    pass


@define
class ExternalRegionRequest(ResourceRequest):
    @classmethod
    def from_dict(cls, init_data: Dict) -> 'ExternalRegionRequest':
        return cls()


class ExternalRegionPermission(Permission):
    """外部版权限"""

    resource_request_cls: Type[ResourceRequest] = ExternalRegionRequest

    def can_create_external_region_app(self, perm_ctx: ExternalRegionPermCtx, raise_exception: bool = True) -> bool:
        return self.can_action(perm_ctx, ExternalRegionAction.CREATE_EXTERNAL_REGION_APP, raise_exception)

    def can_create_external_region_module(self, perm_ctx: ExternalRegionPermCtx, raise_exception: bool = True) -> bool:
        return self.can_action(perm_ctx, ExternalRegionAction.CREATE_EXTERNAL_REGION_MODULE, raise_exception)
