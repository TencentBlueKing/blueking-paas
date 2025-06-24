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
from paasng.platform.sourcectl.models import SourceTypeSpecConfig

from .serializers import (
    SourceTypeSpecConfigCreateInputSLZ,
    SourceTypeSpecConfigDetailOutputSLZ,
    SourceTypeSpecConfigMinimalOutputSLZ,
    SourceTypeSpecConfigUpdateInputSLZ,
)
from .source_templates import source_config_tpl_manager


class SourceTypeSpecViewSet(viewsets.GenericViewSet):
    """代码库相关配置 API"""

    queryset = SourceTypeSpecConfig.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="获取代码库配置列表",
        responses={status.HTTP_200_OK: SourceTypeSpecConfigMinimalOutputSLZ(many=True)},
    )
    def list(self, request):
        queryset = self.get_queryset()
        slz = SourceTypeSpecConfigMinimalOutputSLZ(queryset, many=True)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="获取代码库配置详情",
        responses={status.HTTP_200_OK: SourceTypeSpecConfigDetailOutputSLZ()},
    )
    def retrieve(self, request, pk):
        source_type_spec = get_object_or_404(SourceTypeSpecConfig, pk=pk)
        slz = SourceTypeSpecConfigDetailOutputSLZ(source_type_spec)
        return Response(slz.data)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="创建代码库配置",
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request):
        slz = SourceTypeSpecConfigCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        SourceTypeSpecConfig.objects.create(**data)

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=slz.data["name"],
            data_after=DataDetail(data=slz.data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="更新代码库配置",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update(self, request, pk):
        source_type_spec = get_object_or_404(SourceTypeSpecConfig, pk=pk)
        data_before = DataDetail(data=SourceTypeSpecConfigUpdateInputSLZ(source_type_spec).data)

        slz = SourceTypeSpecConfigUpdateInputSLZ(data=request.data, context={"instance": source_type_spec})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        SourceTypeSpecConfig.objects.filter(pk=pk).update(**data)

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=slz.data["name"],
            data_before=data_before,
            data_after=DataDetail(data=slz.data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="删除代码库配置",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, pk):
        source_type_spec = get_object_or_404(SourceTypeSpecConfig, pk=pk)
        data_before = DataDetail(data=SourceTypeSpecConfigDetailOutputSLZ(source_type_spec).data)

        source_type_spec.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=source_type_spec.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="获取默认配置模板",
        responses={status.HTTP_200_OK: ""},
    )
    def get_default_configs_templates(self, request):
        configs = source_config_tpl_manager.get_all_templates()

        return Response(configs)

    @swagger_auto_schema(
        tags=["plat_mgt.sourcectl"],
        operation_description="获取 spec_cls 列表",
        responses={status.HTTP_200_OK: ""},
    )
    def get_spec_cls_choices(self, request):
        available_spec_cls = [
            "BkSvnSourceTypeSpec",
            "GitHubSourceTypeSpec",
            "GiteeSourceTypeSpec",
            "BareGitSourceTypeSpec",
            "BareSvnSourceTypeSpec",
            "GitLabSourceTypeSpec",
        ]

        # 存在 TcGitSourceTypeSpec 才将其添加到可选项中
        try:
            from paasng.platform.sourcectl.type_specs import TcGitSourceTypeSpec  # noqa: F401

            available_spec_cls.append("TcGitSourceTypeSpec")
        except ImportError:
            pass

        return Response(available_spec_cls)
