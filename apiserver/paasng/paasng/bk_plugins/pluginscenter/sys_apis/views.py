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

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.bk_plugins.pluginscenter import constants, shim
from paasng.bk_plugins.pluginscenter.models import (
    OperationRecord,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfo,
    PluginVisibleRange,
)
from paasng.bk_plugins.pluginscenter.serializers import PluginInstanceSLZ
from paasng.bk_plugins.pluginscenter.sys_apis.serializers import make_sys_plugin_slz_class
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class

API_PERMISSION_CLASSES = [IsAuthenticated, site_perm_class(SiteAction.SYSAPI_MANAGE_APPLICATIONS)]


class SysPluginInstanceViewSet(viewsets.ViewSet):
    """插件开发中心-插件实例相关接口"""

    permission_classes = API_PERMISSION_CLASSES

    @atomic
    def create(self, request, pd_id, **kwargs):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = make_sys_plugin_slz_class(pd, creation=True)(data=request.data, context={"pd": pd})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data
        plugin_tenant_mode = validated_data.pop("plugin_tenant_mode")
        plugin_tenant_id = validated_data.pop("plugin_tenant_id")
        tenant_id = validated_data.pop("tenant_id")
        creator = validated_data.pop("creator")

        plugin = PluginInstance(
            pd=pd,
            language=validated_data["template"].language,
            **validated_data,
            creator=request.user.pk,
            # 插件发布者默认是工具创建者
            publisher=request.user.username,
            # 如果插件不需要审批，则状态设置为开发中
            status=constants.PluginStatus.DEVELOPING,
            # 写入租户相关信息
            plugin_tenant_mode=plugin_tenant_mode.value,
            plugin_tenant_id=plugin_tenant_id,
            tenant_id=tenant_id,
        )
        plugin.save()
        plugin.refresh_from_db()

        # 初始化可见范围
        if hasattr(plugin.pd, "visible_range_definition"):
            PluginVisibleRange.get_or_initialize_with_default(plugin=plugin)

        # 创建默认市场信息
        PluginMarketInfo.objects.create(plugin=plugin, extra_fields={})
        # 创建 IAM 分级管理员
        shim.setup_builtin_grade_manager(plugin)
        # 创建 IAM 用户组
        shim.setup_builtin_user_groups(plugin)
        # 添加默认管理员
        shim.add_role_members(plugin, role=constants.PluginRole.ADMINISTRATOR, usernames=[creator])

        # 操作记录: 创建插件
        OperationRecord.objects.create(
            plugin=plugin,
            operator=user_id_encoder.encode(settings.USER_TYPE, creator),
            action=constants.ActionTypes.CREATE,
            subject=constants.SubjectTypes.PLUGIN,
            tenant_id=tenant_id,
        )
        return Response(
            data=PluginInstanceSLZ(plugin).data,
            status=status.HTTP_201_CREATED,
        )
