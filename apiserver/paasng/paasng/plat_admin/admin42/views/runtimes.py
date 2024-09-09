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

from typing import Type

from django.db import transaction
from django.db.models import QuerySet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.runtime import (
    AppBuildPackSLZ,
    AppSlugBuilderSLZ,
    AppSlugRunnerSLZ,
    SlugBuilderBindRequest,
)
from paasng.plat_admin.admin42.serializers.runtimes import (
    AppSlugBuilderListOutputSLZ,
    BuildPackBindInputSLZ,
    BuildPackCreateInputSLZ,
    BuildPackListOutputSLZ,
    BuildPackUpdateInputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.modules.constants import AppImageType, BuildPackType
from paasng.platform.modules.helpers import SlugbuilderBinder
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner


class RuntimeAdminViewGenerator:
    def __init__(self, name: str, template_name: str, serializer_class: Type, queryset: QuerySet):
        self.name = name
        self.queryset = queryset.all()
        self.serializer_class = serializer_class
        self.template_name = template_name

    def gen_template_view(self):
        """生成模板视图"""

        class TemplateView(GenericTemplateView):
            name = self.name
            queryset = self.queryset.all()
            serializer_class = self.serializer_class
            template_name = self.template_name
            permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

            def get_context_data(self, **kwargs):
                kwargs = super().get_context_data(**kwargs)
                data = self.list(self.request, *self.args, **self.kwargs)
                kwargs["data"] = data
                kwargs["pagination"] = self.get_pagination_context(self.request)
                return kwargs

        return TemplateView

    def gen_model_view_set(self):
        """生成模型操作接口"""

        class APIViewSet(ModelViewSet):
            serializer_class = self.serializer_class
            queryset = self.queryset.all()
            permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

        return APIViewSet


buildpack_generator = RuntimeAdminViewGenerator(
    name="BuildPack管理",
    template_name="admin42/platformmgr/runtime/buildpack_list.html",
    serializer_class=AppBuildPackSLZ,
    queryset=AppBuildPack.objects.order_by("region"),
)

BuildPackTemplateView = buildpack_generator.gen_template_view()
BuildPackAPIViewSet = buildpack_generator.gen_model_view_set()

slugbuilder_generator = RuntimeAdminViewGenerator(
    name="SlugBuilder管理",
    template_name="admin42/platformmgr/runtime/slugbuilder_list.html",
    serializer_class=AppSlugBuilderSLZ,
    queryset=AppSlugBuilder.objects.order_by("region"),
)


class SlugBuilderTemplateView(slugbuilder_generator.gen_template_view()):  # type: ignore
    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["buildpacks"] = {
            item["id"]: item for item in AppBuildPackSLZ(AppBuildPack.objects.all(), many=True).data
        }
        return kwargs


class SlugBuilderAPIViewSet(slugbuilder_generator.gen_model_view_set()):  # type: ignore
    @transaction.atomic
    def set_buildpacks(self, request, *args, **kwargs):
        slz = SlugBuilderBindRequest(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        slugbuilder = self.get_object()
        buildpacks = [AppBuildPack.objects.get(id=buildpack_id) for buildpack_id in data["buildpack_id_list"]]

        binder = SlugbuilderBinder(slugbuilder=slugbuilder)
        binder.set_buildpacks(buildpacks)
        return Response(status=status.HTTP_204_NO_CONTENT)


slugrunner_generator = RuntimeAdminViewGenerator(
    name="SlugRunner管理",
    template_name="admin42/platformmgr/runtime/slugrunner_list.html",
    serializer_class=AppSlugRunnerSLZ,
    queryset=AppSlugRunner.objects.order_by("region"),
)

SlugRunnerTemplateView = slugrunner_generator.gen_template_view()
SlugRunnerAPIViewSet = slugrunner_generator.gen_model_view_set()


# ----------------------------------------------------- new -------------------------------------------------------
class NewBuildPackManageView(GenericTemplateView):
    name = "BuildPack 管理"
    template_name = "admin42/platformmgr/runtimes/buildpack_list.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["regions"] = list(get_all_regions().keys())
        context["buildpack_types"] = dict(BuildPackType.get_choices())
        return context


class NewBuildPackAPIViewSet(GenericViewSet):
    """BuildPack 管理 API 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request):
        """获取所有 BuildPack 列表和详细信息"""
        buildpacks = AppBuildPack.objects.order_by("region")
        return Response(BuildPackListOutputSLZ(buildpacks, many=True).data)

    def get_binding_builders(self, request, pk):
        """获取 BuildPack 绑定的 SlugBuilder 列表和未绑定的 SlugBuilder 列表"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        binding_slugbuilders = buildpack.slugbuilders.all()
        # TAR 类型的 BuildPack 只能绑定 legacy 类型 slugbuilder，OCI 类型 BuildPack 只能绑定 cnb 类型 slugbuilder
        unbinding_slugbuilders = AppSlugBuilder.objects.exclude(type=AppImageType.LEGACY)
        if buildpack.type == BuildPackType.TAR:
            unbinding_slugbuilders = AppSlugBuilder.objects.filter(type=AppImageType.LEGACY)

        unbinding_slugbuilders = unbinding_slugbuilders.exclude(id__in=binding_slugbuilders)

        return Response(
            data={
                "binding_slugbuilders": AppSlugBuilderListOutputSLZ(binding_slugbuilders, many=True).data,
                "unbinding_slugbuilders": AppSlugBuilderListOutputSLZ(unbinding_slugbuilders, many=True).data,
            }
        )

    @transaction.atomic
    @swagger_auto_schema(request_body=BuildPackBindInputSLZ)
    def set_binding_builders(self, request, pk):
        """设置被哪些 SlugBuilder 绑定"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        slz = BuildPackBindInputSLZ(data=request.data, context={"buildpack_type": buildpack.type})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        slugbuilders = [
            AppSlugBuilder.objects.get(id=slugbuilder_id) for slugbuilder_id in data["slugbuilder_id_list"]
        ]
        existing_slugbuilders = buildpack.slugbuilders.all()

        # 找到需要删除的绑定
        to_unbind = [slugbuilder for slugbuilder in existing_slugbuilders if slugbuilder not in slugbuilders]
        for slugbuilder in to_unbind:
            binder = SlugbuilderBinder(slugbuilder=slugbuilder)
            binder.unbind_buildpack(buildpack)
        # 找到需要新增的绑定
        to_bind = [slugbuilder for slugbuilder in slugbuilders if slugbuilder not in existing_slugbuilders]
        for slugbuilder in to_bind:
            binder = SlugbuilderBinder(slugbuilder=slugbuilder)
            binder.bind_buildpack(buildpack)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BUILD_PACK,
            attribute=buildpack.name,
            data_before=DataDetail(
                type=DataType.RAW_DATA,
                data={"binding_slugbuilders": [slugbuilder.name for slugbuilder in existing_slugbuilders]},
            ),
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data={"binding_slugbuilders": [slugbuilder.name for slugbuilder in slugbuilders]},
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(request_body=BuildPackCreateInputSLZ)
    def create(self, request):
        """创建 BuildPack"""
        slz = BuildPackCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.BUILD_PACK,
            attribute=request.data["name"],
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=slz.data,
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(request_body=BuildPackUpdateInputSLZ)
    def update(self, request, pk):
        """更新 BuildPack"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=BuildPackUpdateInputSLZ(buildpack).data,
        )

        slz = BuildPackUpdateInputSLZ(buildpack, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BUILD_PACK,
            attribute=buildpack.name,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=slz.data,
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk):
        """删除 BuildPack"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=BuildPackListOutputSLZ(buildpack).data,
        )
        buildpack.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.BUILD_PACK,
            attribute=buildpack.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
