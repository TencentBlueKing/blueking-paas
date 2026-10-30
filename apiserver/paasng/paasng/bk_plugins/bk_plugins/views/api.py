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

import logging

from django.db.transaction import atomic
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.bk_plugins.bk_plugins import serializers
from paasng.bk_plugins.bk_plugins.apigw import set_distributors
from paasng.bk_plugins.bk_plugins.models import (
    BkPlugin,
    BkPluginDistributor,
    BkPluginTag,
    make_bk_plugin,
)
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class BkPluginProfileViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing BkPlugin's profile"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.BkPluginProfileSLZ})
    def retrieve(self, request, code):
        """获取一个蓝鲸插件的档案信息"""
        profile = self._get_plugin().get_profile()
        return Response(serializers.BkPluginProfileSLZ(instance=profile).data)

    @swagger_auto_schema(
        tags=["bk_plugin"],
        request_body=serializers.BkPluginProfileSLZ,
        responses={200: serializers.BkPluginProfileSLZ},
    )
    def patch(self, request, code):
        """修改蓝鲸插件的档案信息。接口使用补丁（patch）协议，支持每次只传递一个字段。"""
        profile = self._get_plugin().get_profile()
        serializer = serializers.BkPluginProfileSLZ(data=request.data, instance=profile)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 插件使用方，传了才更新
        if "distributors" in serializer.validated_data:
            plugin_app = self.get_application()
            distributors = serializer.validated_data["distributors"]
            try:
                set_distributors(plugin_app, distributors)
            except RuntimeError:
                logger.exception(f"Unable to set distributor for {plugin_app}")
                raise error_codes.UNABLE_TO_SET_DISTRIBUTORS
        return Response(serializers.BkPluginProfileSLZ(instance=profile).data)

    def _get_plugin(self) -> BkPlugin:
        """Get BkPlugin object"""
        application = self.get_application()
        try:
            return make_bk_plugin(application)
        except TypeError:
            raise error_codes.APP_IS_NOT_BK_PLUGIN


class DistributorsViewSet(viewsets.ViewSet):
    """Viewset for plugin distributors"""

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.DistributorSLZ(many=True)})
    def list(self, request):
        """查看系统中所有的“插件使用方（Plugin-Distributor）”，默认按照“创建时间（从旧到新）排序”"""
        distributors = BkPluginDistributor.objects.all().order_by("created")
        return Response(serializers.DistributorSLZ(distributors, many=True).data)


class BkPluginTagsViewSet(viewsets.ViewSet):
    """Viewset for plugin tags"""

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.BkPluginTagSLZ(many=True)})
    def list(self, request):
        """查看系统中所有的“插件分类（Plugin-Tag）”"""
        tags = BkPluginTag.objects.all()
        return Response(serializers.BkPluginTagSLZ(tags, many=True).data)


class DistributorRelsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """Viewset for managing a single bk_plugin's distributor relations"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    @swagger_auto_schema(tags=["bk_plugin"], responses={200: serializers.DistributorSLZ(many=True)})
    def list(self, request, code):
        """查看某个插件应用目前启用的“插件使用方”列表"""
        plugin_app = self.get_application()
        return Response(serializers.DistributorSLZ(plugin_app.distributors, many=True).data)

    @swagger_auto_schema(
        tags=["bk_plugin"],
        request_body=serializers.UpdateDistributorsSLZ,
        responses={200: serializers.DistributorSLZ(many=True)},
    )
    @atomic
    def update(self, request, code):
        """更新某个插件应用所启用的“插件使用方”列表"""
        serializer = serializers.UpdateDistributorsSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        plugin_app = self.get_application()
        distributors = serializer.validated_data["distributors"]
        try:
            set_distributors(plugin_app, distributors)
        except RuntimeError:
            logger.exception(f"Unable to set distributor for {plugin_app}")
            raise error_codes.UNABLE_TO_SET_DISTRIBUTORS
        return Response(serializers.DistributorSLZ(plugin_app.distributors, many=True).data)
