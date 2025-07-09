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

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.misc.monitoring.monitor.models import AppDashboardTemplate
from paasng.plat_admin.admin42.serializers.dashboard_templates import DashboardTemplateSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.applications.constants import AppLanguage


class DashboardTemplateManageView(GenericTemplateView):
    """平台服务管理-仪表盘模板配置"""

    template_name = "admin42/configuration/dashboard_templates.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "仪表盘模板配置"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update({"language_choices": dict(AppLanguage.get_choices())})
        return kwargs


class DashboardTemplateViewSet(ListModelMixin, GenericViewSet):
    """平台服务管理-仪表盘模板配置API"""

    queryset = AppDashboardTemplate.objects.all()
    serializer_class = DashboardTemplateSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]

    def create(self, request):
        """创建仪表盘模板"""
        slz = DashboardTemplateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.DASHBOARD_TEMPLATE,
            attribute=slz.data["name"],
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新仪表盘模板"""
        dashboard_template = self.get_object()
        data_before = DataDetail(data=DashboardTemplateSLZ(dashboard_template).data)

        slz = DashboardTemplateSLZ(dashboard_template, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.DASHBOARD_TEMPLATE,
            attribute=slz.data["name"],
            data_before=data_before,
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """删除仪表盘模板"""
        dashboard_template = self.get_object()
        data_before = DataDetail(data=DashboardTemplateSLZ(dashboard_template).data)
        dashboard_template.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.DASHBOARD_TEMPLATE,
            attribute=dashboard_template.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
