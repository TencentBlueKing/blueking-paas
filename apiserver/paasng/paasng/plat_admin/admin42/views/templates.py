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
from paasng.plat_admin.admin42.serializers.templates import TemplateSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template


class TemplateManageView(GenericTemplateView):
    """平台服务管理-模板配置"""

    template_name = "admin42/configuration/templates.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    name = "模板配置"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update(
            {"type_choices": dict(TemplateType.get_choices()), "language_choices": dict(AppLanguage.get_choices())}
        )
        return kwargs


class TemplateViewSet(ListModelMixin, GenericViewSet):
    """平台服务管理-模板配置API"""

    queryset = Template.objects.all().order_by("is_hidden", "type")
    serializer_class = TemplateSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_APP_TEMPLATES)]
    schema = None

    def create(self, request):
        """创建模板配置"""
        slz = TemplateSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.TEMPLATE,
            attribute=slz.data["name"],
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新模板配置"""
        template = self.get_object()
        data_before = DataDetail(data=TemplateSLZ(template).data)

        slz = TemplateSLZ(template, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.TEMPLATE,
            attribute=slz.data["name"],
            data_before=data_before,
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """删除模板配置"""
        template = self.get_object()
        data_before = DataDetail(data=TemplateSLZ(template).data)
        template.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.TEMPLATE,
            attribute=template.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
