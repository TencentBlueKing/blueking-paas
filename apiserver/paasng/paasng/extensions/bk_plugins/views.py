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
from typing import List, Tuple

import cattr
from django.db.transaction import atomic
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_required
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

from . import serializers
from .apigw import set_distributors
from .logging import PluginLoggingClient
from .models import (
    BkPlugin,
    BkPluginAppQuerySet,
    BkPluginDistributor,
    BkPluginTag,
    make_bk_plugin,
    make_bk_plugins,
    plugin_to_detailed,
)

logger = logging.getLogger(__name__)


class FilterPluginsMixin:
    """A mixin class which provides plugins filtering functionalities"""

    def filter_plugins(self, request: HttpRequest) -> Tuple[List[BkPlugin], LimitOffsetPagination]:
        """A reusable method for filtering plugins, with paginator supports.

        :param request: current Http request
        :param view: current view function,
        """
        serializer = serializers.ListBkPluginsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Query and paginate applications
        applications = BkPluginAppQuerySet().filter(
            search_term=data['search_term'],
            order_by=[data['order_by']],
            has_deployed=data['has_deployed'],
            distributor_code_name=data['distributor_code_name'],
            tag_id=data['tag_id'],
        )
        paginator = LimitOffsetPagination()
        applications = paginator.paginate_queryset(applications, request, self)

        plugins = make_bk_plugins(applications)
        return plugins, paginator


class SysBkPluginsViewset(FilterPluginsMixin, viewsets.ViewSet):
    """Viewset for bk_plugin type applications"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request):
        """查询所有的蓝鲸插件"""
        plugins, paginator = self.filter_plugins(request)
        return paginator.get_paginated_response(serializers.BkPluginSLZ(plugins, many=True).data)

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def retrieve(self, request, code):
        """查询某个蓝鲸插件的详细信息"""
        plugin = get_plugin_or_404(code)
        return Response(serializers.BkPluginDetailedSLZ(plugin_to_detailed(plugin)).data)


class SysBkPluginsBatchViewset(FilterPluginsMixin, viewsets.ViewSet):
    """Viewset for batch operations on bk_plugin type applications"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list_detailed(self, request):
        """批量查询蓝鲸插件的详细信息（包含各环境部署状态等）"""
        plugins, paginator = self.filter_plugins(request)

        # Read extra params
        serializer = serializers.ListDetailedBkPluginsExtraSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        include_addresses = serializer.validated_data['include_addresses']

        results = [
            serializers.BkPluginDetailedSLZ(plugin_to_detailed(plugin, include_addresses)).data for plugin in plugins
        ]
        return paginator.get_paginated_response(results)


class SysBkPluginLogsViewset(viewsets.ViewSet):
    """Viewset for querying bk_plugin's logs"""

    # 网关名称 list_bk_plugin_logs
    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request, code):
        """查询某个蓝鲸插件的结构化日志"""
        serializer = serializers.ListBkPluginLogsSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = PluginLoggingClient(get_plugin_or_404(code))
        logs = client.query(data['trace_id'], data.get('scroll_id'))
        return Response(data=cattr.unstructure(logs))


def get_plugin_or_404(code: str) -> BkPlugin:
    """Get a bk_plugin object by code, raise 404 error when code is invalid

    :param code: plugin code, same with application code
    """
    application = get_object_or_404(BkPluginAppQuerySet().all(), code=code)
    return BkPlugin.from_application(application)


class SysBkPluginTagsViewSet(viewsets.ViewSet):
    """Viewset for querying bk_plugin's tags"""

    @site_perm_required(SiteAction.SYSAPI_READ_APPLICATIONS)
    def list(self, request):
        """View all plugin tags in the system"""
        tags = BkPluginTag.objects.all()
        return Response(serializers.BkPluginTagSLZ(tags, many=True).data)


# User interface ViewSet start


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
        distributors = BkPluginDistributor.objects.all().order_by('created')
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
        distributors = serializer.validated_data['distributors']
        try:
            set_distributors(plugin_app, distributors)
        except RuntimeError:
            logger.exception(f'Unable to set distributor for {plugin_app}')
            raise error_codes.UNABLE_TO_SET_DISTRIBUTORS
        return Response(serializers.DistributorSLZ(plugin_app.distributors, many=True).data)


# User interface ViewSet end
