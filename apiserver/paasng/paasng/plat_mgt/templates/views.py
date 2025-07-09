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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.platform.templates.constants import RenderMethod, TemplateType
from paasng.platform.templates.models import Template

from .serializers import (
    TemplateCreateInputSLZ,
    TemplateDetailOutputSLZ,
    TemplateMinimalOutputSLZ,
    TemplateUpdateInputSLZ,
)


class TemplateViewSet(viewsets.GenericViewSet):
    """配置管理-模板配置 API"""

    queryset = Template.objects.all().order_by("is_hidden", "type")
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="获取模板列表",
        responses={status.HTTP_200_OK: TemplateMinimalOutputSLZ(many=True)},
    )
    def list(self, request):
        queryset = self.get_queryset()
        slz = TemplateMinimalOutputSLZ(queryset, many=True)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="获取单个模板详情",
        responses={status.HTTP_200_OK: TemplateDetailOutputSLZ()},
    )
    def retrieve(self, request, pk):
        tmpl = get_object_or_404(Template, pk=pk)
        slz = TemplateDetailOutputSLZ(tmpl)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="创建模板",
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request):
        slz = TemplateCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        Template.objects.create(**data)

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.TEMPLATE,
            attribute=data["name"],
            data_after=DataDetail(data=data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="更新模板",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, pk):
        template = get_object_or_404(Template, pk=pk)
        data_before = DataDetail(data=TemplateDetailOutputSLZ(template).data)

        slz = TemplateUpdateInputSLZ(data=request.data, context={"instance": template})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 更新模板
        Template.objects.filter(id=template.id).update(**data)

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.TEMPLATE,
            attribute=data["name"],
            data_before=data_before,
            data_after=DataDetail(data=data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="删除模板",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, pk):
        tmpl = get_object_or_404(Template, pk=pk)
        data_before = DataDetail(data=TemplateDetailOutputSLZ(tmpl).data)

        tmpl.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.TEMPLATE,
            attribute=tmpl.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.templates"],
        operation_description="获取模板相关的元数据",
        responses={status.HTTP_200_OK: ""},
    )
    def get_templates_metadata(self, request):
        result = {
            "repo_types": [{"name": name, "label": label} for name, label in get_sourcectl_types().get_choices()],
            "application_types": [{"name": name, "label": label} for name, label in AppLanguage.get_django_choices()],
            "template_types": [{"name": name, "label": label} for name, label in TemplateType.get_django_choices()],
            "render_methods": [{"name": name, "label": label} for name, label in RenderMethod.get_django_choices()],
        }
        return Response(result)
