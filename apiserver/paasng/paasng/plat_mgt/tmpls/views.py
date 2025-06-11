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

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.platform.templates.models import Template
from paasng.utils.error_codes import error_codes

from .serializers import (
    TemplateDetailOutputSLZ,
    TemplateMinimalOutputSLZ,
    TemplateUpsertInputSLZ,
)


class TemplateViewSet(viewsets.GenericViewSet):
    """配置管理-模板配置 API"""

    queryset = Template.objects.all().order_by("is_hidden", "type")
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.tmpls"],
        operation_description="获取模板列表",
        responses={status.HTTP_200_OK: TemplateMinimalOutputSLZ(many=True)},
    )
    def list(self, request):
        """获取模板列表"""
        queryset = self.get_queryset()
        slz = TemplateMinimalOutputSLZ(queryset, many=True)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.tmpls"],
        operation_description="获取模板详情",
        responses={status.HTTP_200_OK: TemplateDetailOutputSLZ()},
    )
    def retrieve(self, request, template_id):
        """获取单个模板详情"""
        tmpl = get_object_or_404(Template, id=template_id)
        slz = TemplateDetailOutputSLZ(tmpl)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.tmpls"],
        operation_description="创建模板",
        responses={status.HTTP_201_CREATED: None},
    )
    def create(self, request):
        """创建模板"""
        slz = TemplateUpsertInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            Template.objects.create(**data)
        except IntegrityError as e:
            # 检查是否是名称唯一性约束错误
            if "name" in str(e) or "UNIQUE constraint failed" in str(e):
                raise error_codes.CANNOT_CREATE_TMPL.f(_("名称已存在，请使用其他名称"))
            raise

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.TEMPLATE,
            attribute=data["name"],
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.tmpls"],
        operation_description="更新模板",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def update(self, request, template_id):
        """更新模板"""
        tmpl = get_object_or_404(Template, id=template_id)
        data_before = DataDetail(type=DataType.RAW_DATA, data=TemplateDetailOutputSLZ(tmpl).data)

        slz = TemplateUpsertInputSLZ(tmpl, data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        Template.objects.filter(id=template_id).update(**data)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.TEMPLATE,
            attribute=data["name"],
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.tmpls"],
        operation_description="删除模板",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def destroy(self, request, template_id):
        """删除模板"""
        tmpl = get_object_or_404(Template, id=template_id)
        data_before = DataDetail(type=DataType.RAW_DATA, data=TemplateDetailOutputSLZ(tmpl).data)

        tmpl.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.TEMPLATE,
            attribute=tmpl.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
