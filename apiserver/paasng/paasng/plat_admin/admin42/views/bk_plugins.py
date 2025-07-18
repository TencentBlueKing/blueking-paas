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

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from paasng.bk_plugins.bk_plugins.models import BkPluginDistributor, BkPluginTag
from paasng.bk_plugins.pluginscenter import constants as plugin_constants
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as members_api
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.bk_plugins import (
    BkPluginDistributorSLZ,
    BKPluginMembersManageReqSLZ,
    BKPluginTagSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView


class BKPluginTagManageView(GenericTemplateView):
    """平台服务管理-插件分类配置"""

    # 插件分类配置, 使用 "插件配置" 为了前端导航高亮
    template_name = "admin42/settings/bk_plugin/bk_plugin_tag.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "插件配置"


class BKPluginTagView(GenericViewSet, ListModelMixin):
    """平台服务管理-插件分类配置API"""

    queryset = BkPluginTag.objects.all()
    serializer_class = BKPluginTagSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]

    def create(self, request):
        """创建插件分类"""
        slz = BKPluginTagSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.BKPLUGIN_TAG,
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新插件分类"""
        plugin_tag = self.get_object()
        data_before = DataDetail(data=BKPluginTagSLZ(plugin_tag).data)

        slz = BKPluginTagSLZ(plugin_tag, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_TAG,
            data_before=data_before,
            data_after=DataDetail(data=BKPluginTagSLZ(plugin_tag).data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """删除插件分类"""
        plugin_tag = self.get_object()
        data_before = DataDetail(data=BKPluginTagSLZ(plugin_tag).data)
        plugin_tag.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.BKPLUGIN_TAG,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BKPluginDistributorsManageView(GenericTemplateView):
    """平台服务管理-插件使用方配置"""

    # 插件使用方配置, 使用 "插件配置" 为了前端导航高亮
    template_name = "admin42/settings/bk_plugin/bk_plugin_distributor.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "插件配置"


class BKPluginDistributorsView(GenericViewSet, ListModelMixin):
    """平台服务管理-插件使用方配置API"""

    queryset = BkPluginDistributor.objects.all()
    serializer_class = BkPluginDistributorSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]

    def create(self, request):
        """创建插件使用方"""
        slz = BkPluginDistributorSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.BKPLUGIN_DISTRIBUTOR,
            data_after=DataDetail(data=slz.data),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新插件使用方"""
        plugin_distributor = self.get_object()
        data_before = DataDetail(data=BkPluginDistributorSLZ(plugin_distributor).data)
        slz = BkPluginDistributorSLZ(plugin_distributor, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_DISTRIBUTOR,
            data_before=data_before,
            data_after=DataDetail(data=BkPluginDistributorSLZ(plugin_distributor).data),
        )
        return Response(slz.data)

    def destroy(self, request, *args, **kwargs):
        """删除插件使用方"""
        plugin_distributor = self.get_object()
        data_before = DataDetail(data=BkPluginDistributorSLZ(plugin_distributor).data)
        plugin_distributor.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.BKPLUGIN_DISTRIBUTOR,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BKPluginMembersManageViewSet(ViewSet):
    """插件成员管理接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

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

    def update(self, request, code):
        """将用户添加或取消为某个角色的成员"""
        slz = BKPluginMembersManageReqSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        username = request.user.username
        plugin = get_object_or_404(PluginInstance, id=code)

        data_before = self._gen_data_detail(plugin, username)

        if data["action"] == "add":
            members_api.add_role_members(plugin, plugin_constants.PluginRole(data["role"]), [username])
        if data["action"] == "delete":
            members_api.delete_role_members(plugin, plugin_constants.PluginRole(data["role"]), [username])

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_MEMBER,
            app_code=code,
            data_before=data_before,
            data_after=self._gen_data_detail(plugin, username),
        )

        return Response(status=status.HTTP_200_OK)


def is_plugin_instance_exist(code: str) -> bool:
    return PluginInstance.objects.filter(id=code).exists()


def is_user_plugin_admin(code: str, username: str) -> bool:
    """判断用户是否是插件管理员"""
    plugin = PluginInstance.objects.filter(id=code).first()
    if not plugin:
        return False
    roles = members_api.fetch_user_roles(plugin, username)
    return plugin_constants.PluginRole.ADMINISTRATOR in roles
