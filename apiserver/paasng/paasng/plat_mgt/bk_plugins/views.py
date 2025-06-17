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

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.bk_plugins.pluginscenter import constants as plugin_constants
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as members_api
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.utils.error_codes import error_codes


class BKPluginMembersManageViewSet(ViewSet):
    """插件成员管理接口"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def become_admin(self, request, app_code):
        """成为插件管理员"""

        username = request.user.username
        plugin = get_object_or_404(PluginInstance, id=app_code)
        role = plugin_constants.PluginRole.ADMINISTRATOR.value

        data_before = self._gen_data_detail(plugin, username)

        # 多租户环境下不允许添加不同租户的成员成为管理员
        if settings.ENABLE_MULTI_TENANT_MODE and plugin.tenant_id != request.user.tenant_id:
            raise error_codes.MEMBERSHIP_CREATE_FAILED.f("不允许添加不同租户的成员")

        members_api.add_role_members(plugin, plugin_constants.PluginRole(role), [username])

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_MEMBER,
            app_code=app_code,
            data_before=data_before,
            data_after=self._gen_data_detail(plugin, username),
        )

        return Response(status=status.HTTP_200_OK)

    def remove_admin(self, request, app_code):
        """退出插件管理员身份"""

        username = request.user.username
        plugin = get_object_or_404(PluginInstance, id=app_code)
        role = plugin_constants.PluginRole.ADMINISTRATOR.value

        data_before = self._gen_data_detail(plugin, username)

        members_api.delete_role_members(plugin, plugin_constants.PluginRole(role), [username])

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_MEMBER,
            app_code=app_code,
            data_before=data_before,
            data_after=self._gen_data_detail(plugin, username),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _gen_data_detail(code: str, username: str) -> DataDetail:
        return DataDetail(
            data={
                "username": username,
                "roles": [
                    plugin_constants.PluginRole(role).name.lower()
                    for role in members_api.fetch_user_roles(code, username)
                ],
            },
        )


def is_plugin_instance_exist(code: str) -> bool:
    return PluginInstance.objects.filter(id=code).exists()


def is_user_plugin_admin(code: str, username: str) -> bool:
    """判断用户是否是插件管理员"""
    plugin = PluginInstance.objects.filter(id=code).first()
    if not plugin:
        return False
    roles = members_api.fetch_user_roles(plugin, username)
    return plugin_constants.PluginRole.ADMINISTRATOR in roles
