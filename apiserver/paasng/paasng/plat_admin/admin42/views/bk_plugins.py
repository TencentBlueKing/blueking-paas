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

from rest_framework import status
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paasng.bk_plugins.bk_plugins.models import BkPluginDistributor, BkPluginTag
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.bk_plugins import BkPluginDistributorSLZ, BKPluginTagSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView


class BKPluginTagManageView(GenericTemplateView):
    """平台服务管理-插件分类配置"""

    template_name = "admin42/configuration/bk_plugin_tag.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "插件分类配置"


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
            data_after=DataDetail(type=DataType.RAW_DATA, data=slz.data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新插件分类"""
        plugin_tag = self.get_object()
        data_before = DataDetail(type=DataType.RAW_DATA, data=BKPluginTagSLZ(plugin_tag).data)

        slz = BKPluginTagSLZ(plugin_tag, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_TAG,
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=BKPluginTagSLZ(plugin_tag).data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """删除插件分类"""
        plugin_tag = self.get_object()
        data_before = DataDetail(type=DataType.RAW_DATA, data=BKPluginTagSLZ(plugin_tag).data)
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

    template_name = "admin42/configuration/bk_plugin_distributor.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "插件使用方配置"


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
            data_after=DataDetail(type=DataType.RAW_DATA, data=slz.data),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新插件使用方"""
        plugin_distributor = self.get_object()
        data_before = DataDetail(type=DataType.RAW_DATA, data=BkPluginDistributorSLZ(plugin_distributor).data)
        slz = BkPluginDistributorSLZ(plugin_distributor, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BKPLUGIN_DISTRIBUTOR,
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=BkPluginDistributorSLZ(plugin_distributor).data),
        )
        return Response(slz.data)

    def destroy(self, request, *args, **kwargs):
        """删除插件使用方"""
        plugin_distributor = self.get_object()
        data_before = DataDetail(type=DataType.RAW_DATA, data=BkPluginDistributorSLZ(plugin_distributor).data)
        plugin_distributor.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.BKPLUGIN_DISTRIBUTOR,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
