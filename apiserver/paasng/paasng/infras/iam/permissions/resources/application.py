# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import logging
from datetime import datetime, timedelta
from typing import Dict, Type

from attrs import define, field, validators
from bkpaas_auth.core.encoder import user_id_encoder
from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from iam.exceptions import AuthAPIError

from paasng.infras.iam.constants import ResourceType
from paasng.infras.iam.permissions.perm import PermCtx, Permission, ResCreatorAction, validate_empty
from paasng.infras.iam.permissions.request import ResourceRequest

logger = logging.getLogger(__name__)


class AppAction(StrStructuredEnum):
    """蓝鲸 PaaS 应用相关权限"""

    # 应用基础信息查看
    VIEW_BASIC_INFO = EnumField("view_basic_info", label=_("基础信息查看"))
    # 应用基础信息编辑（含文档管理）
    EDIT_BASIC_INFO = EnumField("edit_basic_info", label=_("基础信息编辑"))
    # 应用删除/下架
    DELETE_APPLICATION = EnumField("delete_application", label=_("应用删除"))
    # 成员管理
    MANAGE_MEMBERS = EnumField("manage_members", label=_("成员管理"))
    # 访问控制（用户白名单限制）
    MANAGE_ACCESS_CONTROL = EnumField("manage_access_control", label=_("访问控制管理"))
    # 应用市场管理
    MANAGE_APP_MARKET = EnumField("manage_app_market", label=_("应用市场管理"))
    # 数据统计（网站访问，访问日志，自定义事件等）
    DATA_STATISTICS = EnumField("data_statistics", label=_("数据统计"))
    # 基础开发（部署应用，进程管理，日志查看，镜像凭证，代码库，环境配置，访问入口，增强服务基础等）
    BASIC_DEVELOP = EnumField("basic_develop", label=_("基础开发"))
    # 云 API 管理（查看/申请等）
    MANAGE_CLOUD_API = EnumField("manage_cloud_api", label=_("云 API 管理"))
    # 告警记录查看
    VIEW_ALERT_RECORDS = EnumField("view_alert_records", label=_("告警记录查看"))
    # 告警策略配置
    EDIT_ALERT_POLICY = EnumField("edit_alert_policy", label=_("告警策略配置"))
    # 增强服务管理（启用/删除等）
    MANAGE_ADDONS_SERVICES = EnumField("manage_addons_services", label=_("增强服务管理"))
    # 部署环境限制管理
    MANAGE_ENV_PROTECTION = EnumField("manage_env_protection", label=_("部署环境限制管理"))
    # 模块管理（新建/删除等）
    MANAGE_MODULE = EnumField("manage_module", label=_("模块管理"))


@define
class AppCreatorAction(ResCreatorAction):
    code: str
    name: str
    resource_type: ResourceType = ResourceType.Application

    def to_data(self) -> Dict:
        data = super().to_data()
        return {"id": self.code, "name": self.name, **data}


@define
class AppPermCtx(PermCtx):
    code = field(validator=[validators.instance_of(str), validate_empty])

    def __attrs_post_init__(self):
        from paasng.platform.applications.tenant import get_tenant_id_for_app

        self.tenant_id = get_tenant_id_for_app(self.code)

    @property
    def resource_id(self) -> str:
        return self.code


@define
class AppRequest(ResourceRequest):
    code = field(validator=[validators.instance_of(str), validate_empty])
    resource_type = field(init=False, default=ResourceType.Application)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "AppRequest":
        return cls(code=init_data["code"])


class ApplicationPermission(Permission):
    """应用权限"""

    resource_type: str = ResourceType.Application
    resource_request_cls: Type[ResourceRequest] = AppRequest

    def get_method_by_action(self, action: AppAction):
        return getattr(self, f"can_{action.value}")

    def can_view_basic_info(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_action(perm_ctx, AppAction.VIEW_BASIC_INFO, raise_exception)

    def can_edit_basic_info(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.EDIT_BASIC_INFO, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_delete_application(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx,
            [AppAction.DELETE_APPLICATION, AppAction.EDIT_BASIC_INFO, AppAction.VIEW_BASIC_INFO],
            raise_exception,
        )

    def can_manage_members(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.MANAGE_MEMBERS, AppAction.EDIT_BASIC_INFO, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_manage_access_control(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx,
            [AppAction.MANAGE_ACCESS_CONTROL, AppAction.EDIT_BASIC_INFO, AppAction.VIEW_BASIC_INFO],
            raise_exception,
        )

    def can_manage_app_market(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx,
            [AppAction.MANAGE_APP_MARKET, AppAction.VIEW_BASIC_INFO],
            raise_exception,
        )

    def can_data_statistics(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.DATA_STATISTICS, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_basic_develop(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(perm_ctx, [AppAction.BASIC_DEVELOP, AppAction.VIEW_BASIC_INFO], raise_exception)

    def can_manage_cloud_api(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.MANAGE_CLOUD_API, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_view_alert_records(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.VIEW_ALERT_RECORDS, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_edit_alert_policy(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx,
            [AppAction.EDIT_ALERT_POLICY, AppAction.VIEW_ALERT_RECORDS, AppAction.VIEW_BASIC_INFO],
            raise_exception,
        )

    def can_manage_addons_services(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.MANAGE_ADDONS_SERVICES, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_manage_env_protection(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(
            perm_ctx, [AppAction.MANAGE_ENV_PROTECTION, AppAction.VIEW_BASIC_INFO], raise_exception
        )

    def can_manage_module(self, perm_ctx: AppPermCtx, raise_exception: bool = True) -> bool:
        perm_ctx.validate_resource_id()
        return self.can_multi_actions(perm_ctx, [AppAction.MANAGE_MODULE, AppAction.VIEW_BASIC_INFO], raise_exception)

    def gen_user_app_filters(self, username: str, tenant_id: str):
        """
        生成用户有权限的应用 Django 过滤条件

        所有应用的角色都会有基础信息查看权限
        """
        request = self._make_request(username, AppAction.VIEW_BASIC_INFO)
        return self._gen_app_filters_by_request(request, tenant_id)

    def gen_develop_app_filters(self, username: str, tenant_id: str):
        """
        生成用户有开发者权限的应用 Django 过滤条件

        管理者，开发者才会有基础开发权限
        """
        request = self._make_request(username, AppAction.BASIC_DEVELOP)
        return self._gen_app_filters_by_request(request, tenant_id)

    def _gen_app_filters_by_request(self, request, tenant_id: str):
        """根据 IAM Auth Request 生成 Django 的过滤器"""
        key_mapping = {"application.id": "code"}

        try:
            filters = self._make_iam(tenant_id).make_filter(request, key_mapping=key_mapping)
        except AuthAPIError as e:
            logger.warning("generate user app filters failed: %s", str(e))
            return None

        # 因权限中心同步（用户组成员信息 —> 具体的权限策略）存在时延（约 20s），
        # 因此在应用创建后的短时间内，需特殊豁免以免在列表页无法查询到最新的应用
        perm_exempt_filter = Q(
            owner=user_id_encoder.encode(settings.USER_TYPE, request.subject.id),
            created__gt=datetime.now() - timedelta(seconds=settings.IAM_PERM_EFFECTIVE_TIMEDELTA),
        )
        if not filters:
            return perm_exempt_filter

        # 过滤掉非当前租户的应用
        return (filters & Q(tenant_id=tenant_id)) | perm_exempt_filter
