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

from paasng.accessories.smart_advisor.models import DeployFailurePattern, DocumentaryLink
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit import constants
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.smart_advisor import DeployFailurePatternSLZ, DocumentaryLinkSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView


class DocumentaryLinkView(GenericTemplateView):
    """文档链接管理页"""

    template_name = "admin42/platformmgr/documentary_link.html"
    queryset = DocumentaryLink.objects.all()
    serializer_class = DocumentaryLinkSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "文档管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["documents"] = self.list(self.request, *self.args, **self.kwargs)
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs


class DocumentaryLinkManageViewSet(ListModelMixin, GenericViewSet):
    """智能顾问-文档管理API"""

    serializer_class = DocumentaryLinkSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    queryset = DocumentaryLink.objects.all()

    def create(self, request):
        """创建文档"""
        slz = DocumentaryLinkSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.CREATE,
            target=constants.OperationTarget.DOCUMENT,
            data_after=DataDetail(type=constants.DataType.RAW_DATA, data=slz.data),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """删除文档"""
        instance = self.get_object()
        data_before = DataDetail(type=constants.DataType.RAW_DATA, data=DocumentaryLinkSLZ(instance).data)
        instance.delete()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.DELETE,
            target=constants.OperationTarget.DOCUMENT,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """更新文档"""
        instance = self.get_object()
        slz = DocumentaryLinkSLZ(instance, data=request.data)
        slz.is_valid(raise_exception=True)
        data_before = DataDetail(type=constants.DataType.RAW_DATA, data=DocumentaryLinkSLZ(instance).data)
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.MODIFY,
            target=constants.OperationTarget.DOCUMENT,
            data_before=data_before,
            data_after=DataDetail(type=constants.DataType.RAW_DATA, data=slz.data),
        )
        return Response(slz.data)


class DeployFailurePatternView(GenericTemplateView):
    """失败提示管理"""

    template_name = "admin42/platformmgr/deploy_failure_tips.html"
    queryset = DeployFailurePattern.objects.all()
    serializer_class = DeployFailurePatternSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "失败提示管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["failure_tips"] = self.list(self.request, *self.args, **self.kwargs)
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs


class DeployFailurePatternManageViewSet(ListModelMixin, GenericViewSet):
    """智能顾问-失败提示管理API"""

    serializer_class = DeployFailurePatternSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    queryset = DeployFailurePattern.objects.all()

    def create(self, request):
        """创建失败提示"""
        slz = DeployFailurePatternSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.CREATE,
            target=constants.OperationTarget.DEPLOY_FAILURE_TIPS,
            data_after=DataDetail(type=constants.DataType.RAW_DATA, data=slz.data),
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """删除失败提示"""
        instance = self.get_object()
        data_before = DataDetail(type=constants.DataType.RAW_DATA, data=DeployFailurePatternSLZ(instance).data)
        instance.delete()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.DELETE,
            target=constants.OperationTarget.DEPLOY_FAILURE_TIPS,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """更新失败提示"""
        instance = self.get_object()
        slz = DeployFailurePatternSLZ(instance, data=request.data)
        slz.is_valid(raise_exception=True)
        data_before = DataDetail(type=constants.DataType.RAW_DATA, data=DeployFailurePatternSLZ(instance).data)
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.MODIFY,
            target=constants.OperationTarget.DEPLOY_FAILURE_TIPS,
            data_before=data_before,
            data_after=DataDetail(type=constants.DataType.RAW_DATA, data=slz.data),
        )
        return Response(slz.data)
