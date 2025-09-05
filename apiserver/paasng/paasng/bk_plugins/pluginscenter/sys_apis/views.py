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
from collections import defaultdict
from typing import Dict, List

from bkpaas_auth.models import user_id_encoder
from blue_krill.web.std_error import APIError as StdAPIError
from django.conf import settings
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.bk_plugins.pluginscenter import constants, shim
from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as members_api
from paasng.bk_plugins.pluginscenter.models import (
    OperationRecord,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfo,
    PluginVisibleRange,
)
from paasng.bk_plugins.pluginscenter.serializers import PluginInstanceSLZ
from paasng.bk_plugins.pluginscenter.sys_apis.serializers import PluginMemberInputSLZ, make_sys_plugin_slz_class
from paasng.bk_plugins.pluginscenter.thirdparty.instance import create_instance
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class

logger = logging.getLogger(__name__)


class SysPluginApiViewSet(viewsets.ViewSet):
    """插件开发中心提供的应用态 API"""

    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_APPLICATIONS)]

    @atomic
    def create(self, request, pd_id, **kwargs):
        pd = get_object_or_404(PluginDefinition, identifier=pd_id)
        slz = make_sys_plugin_slz_class(pd, creation=True)(data=request.data, context={"pd": pd})
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data
        plugin_tenant_mode = validated_data.pop("plugin_tenant_mode")
        creator = validated_data.pop("creator")
        creator_id = user_id_encoder.encode(settings.USER_TYPE, creator)

        # 会从 slz 中解析出 name_zh_cn、name_cn 等国际化字段，并且对各个语言都要赋初始化值，所以不直接使用 PluginInstance.objects.create()
        plugin = PluginInstance(
            pd=pd,
            language=validated_data["template"].language,
            **validated_data,
            creator=creator_id,
            # 插件发布者默认是工具创建者
            publisher=creator,
            status=constants.PluginStatus.DEVELOPING,
            # 写入租户相关信息
            plugin_tenant_mode=plugin_tenant_mode.value,
        )
        plugin.save()
        plugin.refresh_from_db()

        # 初始化可见范围
        if hasattr(plugin.pd, "visible_range_definition"):
            PluginVisibleRange.get_or_initialize_with_default(plugin=plugin)

        # 调用第三方系统API
        if plugin.pd.basic_info_definition.api.create:
            try:
                api_call_success = create_instance(plugin.pd, plugin, creator)
            except StdAPIError:
                logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
                raise
            except Exception:
                logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
                raise error_codes.THIRD_PARTY_API_ERROR

            if not api_call_success:
                raise error_codes.THIRD_PARTY_API_ERROR

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
            operator=creator_id,
            action=constants.ActionTypes.CREATE,
            subject=constants.SubjectTypes.PLUGIN,
            tenant_id=plugin.tenant_id,
        )
        return Response(
            data=PluginInstanceSLZ(plugin).data,
            status=status.HTTP_201_CREATED,
        )

    def sync_members(self, request, pd_id, plugin_id, **kwargs):
        """同步插件成员权限
        :param pd_id: 插件定义 ID
        :param plugin_id: 插件实例 ID
        """
        plugin = get_object_or_404(PluginInstance, pd__identifier=pd_id, id=plugin_id)

        slz = PluginMemberInputSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        existed_members = {m.username: m for m in members_api.fetch_plugin_members(plugin)}

        # 需要新增的权限：{角色: [用户名]}
        need_to_add: Dict[PluginRole, List[str]] = defaultdict(list)
        # 需要回收的权限：{用户名: [角色]}
        need_to_clean: Dict[str, List[PluginRole]] = defaultdict(list)

        # 当前需要保留的用户集合
        current_members = set()
        for member in data:
            role = PluginRole(member["role"]["id"])
            username = member["username"]
            current_members.add(username)

            # 处理已存在的成员
            if username in existed_members:
                original_role = existed_members[username].role.id
                if original_role != role:
                    # 角色变更时，需要回收旧角色并添加新角色
                    need_to_clean[username].append(original_role)
                    need_to_add[role].append(username)
            else:
                # 新增用户直接添加角色
                need_to_add[role].append(username)

        # 删除用户
        if redundant_users := existed_members.keys() - current_members:
            members_api.remove_user_all_roles(plugin, usernames=list(redundant_users))
        # 添加用户权限
        for role, usernames in need_to_add.items():
            members_api.add_role_members(plugin, role=role, usernames=usernames)
        # 回收用户多余的权限
        for username, roles in need_to_clean.items():
            for role in roles:
                members_api.delete_role_members(plugin, role=role, usernames=[username])
        return Response(data={})
