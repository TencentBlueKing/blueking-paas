# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
import logging

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.http import HttpRequest
from django.utils.translation import gettext as _
from rest_framework import permissions

from paas_wl.platform.applications.struct_models import Application, SitePermissions

logger = logging.getLogger(__name__)


class AppAction(str, StructuredEnum):
    """蓝鲸 PaaS 应用相关权限"""

    # 应用基础信息查看
    VIEW_BASIC_INFO = EnumField('view_basic_info', label=_('基础信息查看'))
    # 应用基础信息编辑（含文档管理）s
    EDIT_BASIC_INFO = EnumField('edit_basic_info', label=_('基础信息编辑'))
    # 应用删除/下架
    DELETE_APPLICATION = EnumField('delete_application', label=_('应用删除'))
    # 成员管理
    MANAGE_MEMBERS = EnumField('manage_members', label=_('成员管理'))
    # 访问控制（用户白名单限制）
    MANAGE_ACCESS_CONTROL = EnumField('manage_access_control', label=_('访问控制管理'))
    # 应用市场管理
    MANAGE_APP_MARKET = EnumField('manage_app_market', label=_('应用市场管理'))
    # 数据统计（网站访问，访问日志，自定义事件等）
    DATA_STATISTICS = EnumField('data_statistics', label=_('数据统计'))
    # 基础开发（部署应用，进程管理，日志查看，镜像凭证，代码库，环境配置，访问入口，增强服务基础等）
    BASIC_DEVELOP = EnumField('basic_develop', label=_('基础开发'))
    # 云 API 管理（查看/申请等）
    MANAGE_CLOUD_API = EnumField('manage_cloud_api', label=_('云 API 管理'))
    # 告警记录查看
    VIEW_ALERT_RECORDS = EnumField('view_alert_records', label=_('告警记录查看'))
    # 告警策略配置
    EDIT_ALERT_POLICY = EnumField('edit_alert_policy', label=_('告警策略配置'))
    # 增强服务管理（启用/删除等）
    MANAGE_ADDONS_SERVICES = EnumField('manage_addons_services', label=_('增强服务管理'))
    # 部署环境限制管理
    MANAGE_ENV_PROTECTION = EnumField('manage_env_protection', label=_('部署环境限制管理'))
    # 模块管理（新建/删除等）
    MANAGE_MODULE = EnumField('manage_module', label=_('模块管理'))


def application_perm_class(action: AppAction):
    """A factory function which generates a Permission class for DRF permission check"""

    class Permission(permissions.BasePermission):
        """Check if an user has permission to operate an application"""

        def has_object_permission(self, request: HttpRequest, view, obj: Application):
            assert isinstance(obj, Application), 'Only support "Application" object'

            # TODO: Support permission check by requesting remote endpoints
            app_perms = request.perms_in_place.get_application_perms(obj)
            ret = app_perms.check_allowed(action)
            logger.debug('Permission check result, user: %s, obj: %s, result: %s', request.user, obj, ret)
            return ret

    return Permission


class SiteAction(str, StructuredEnum):
    """蓝鲸 PaaS 平台全局功能相关权限"""

    # 能否访问蓝鲸 PaaS
    VISIT_SITE = EnumField('visit_site', label=_('平台页面查看'))
    # 平台管理（增强服务，运行时，应用集群，应用资源方案，应用管理，用户管理，代码库配置管理等）
    MANAGE_PLATFORM = EnumField('manage_platform', label=_('平台管理'))
    # 应用模板管理（场景/应用模板管理）
    MANAGE_APP_TEMPLATES = EnumField('manage_app_templates', label=_('应用模板管理'))
    # 平台运营（查看平台运营数据）
    OPERATE_PLATFORM = EnumField('operate_platform', label=_('平台运营'))


def site_perm_class(action: SiteAction):
    """A factory function which generates a Permission class for DRF permission check"""

    class Permission(permissions.BasePermission):
        """Check if an user has permission on site"""

        def has_permission(self, request, view):
            site_perms: SitePermissions = request.perms_in_place.site_perms
            if site_perms is None:
                return False
            return site_perms.check_allowed(action)

        def has_object_permission(self, request, view, obj):
            return super().has_permission(request, view)

    return Permission
