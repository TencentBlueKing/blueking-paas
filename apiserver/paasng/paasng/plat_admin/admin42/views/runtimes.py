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
    AppSlugBuilderBindInputSLZ,
    AppSlugBuilderCreateInputSLZ,
    AppSlugBuilderListOutputSLZ,
    AppSlugBuilderUpdateInputSLZ,
    BuildPackBindInputSLZ,
    BuildPackCreateInputSLZ,
    BuildPackListOutputSLZ,
    BuildPackUpdateInputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.models.steps import StepMetaSet
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
LegacyBuildPackAPIViewSet = buildpack_generator.gen_model_view_set()

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


class LegacySlugBuilderAPIViewSet(slugbuilder_generator.gen_model_view_set()):  # type: ignore
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
class BuildPackManageView(GenericTemplateView):
    name = "BuildPack 管理"
    template_name = "admin42/platformmgr/runtimes/buildpacks.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["regions"] = list(get_all_regions().keys())
        context["buildpack_types"] = dict(BuildPackType.get_choices())
        return context


class BuildPackAPIViewSet(GenericViewSet):
    """BuildPack 管理 API 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request):
        """获取所有 BuildPack 列表和详细信息"""
        buildpacks = AppBuildPack.objects.order_by("region")
        return Response(BuildPackListOutputSLZ(buildpacks, many=True).data)

    def get_bound_builders(self, request, pk):
        """获取 BuildPack 绑定的 SlugBuilder 列表和未绑定的 SlugBuilder 列表"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        bound_slugbuilders = buildpack.slugbuilders.all()
        # TAR 类型的 BuildPack 只能绑定 legacy 类型 slugbuilder，OCI 类型 BuildPack 只能绑定 cnb 类型 slugbuilder
        unbound_slugbuilders = AppSlugBuilder.objects.exclude(id__in=bound_slugbuilders)

        if buildpack.type == BuildPackType.TAR:
            unbound_slugbuilders = unbound_slugbuilders.filter(type=AppImageType.LEGACY)
        else:
            unbound_slugbuilders = unbound_slugbuilders.filter(type=AppImageType.CNB)

        return Response(
            data={
                "bound_slugbuilders": AppSlugBuilderListOutputSLZ(bound_slugbuilders, many=True).data,
                "unbound_slugbuilders": AppSlugBuilderListOutputSLZ(unbound_slugbuilders, many=True).data,
            }
        )

    @transaction.atomic
    def set_bound_builders(self, request, pk):
        """设置被哪些 SlugBuilder 绑定"""
        buildpack = AppBuildPack.objects.get(pk=pk)
        slz = BuildPackBindInputSLZ(data=request.data, context={"buildpack_type": buildpack.type})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        slugbuilders = AppSlugBuilder.objects.filter(id__in=data["slugbuilder_ids"])
        existing_slugbuilders = buildpack.slugbuilders.all()
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data={"bound_slugbuilders": [slugbuilder.name for slugbuilder in existing_slugbuilders]},
        )

        # 找到需要删除的绑定
        waiting_unbind_slugbuilders = existing_slugbuilders.exclude(id__in=slugbuilders)
        for slugbuilder in waiting_unbind_slugbuilders:
            binder = SlugbuilderBinder(slugbuilder=slugbuilder)
            binder.unbind_buildpack(buildpack)
        # 找到需要新增的绑定
        waiting_bind_slugbuilders = slugbuilders.exclude(id__in=existing_slugbuilders)
        for slugbuilder in waiting_bind_slugbuilders:
            binder = SlugbuilderBinder(slugbuilder=slugbuilder)
            binder.bind_buildpack(buildpack)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.BUILDPACK,
            attribute=buildpack.name,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data={"bound_slugbuilders": [slugbuilder.name for slugbuilder in slugbuilders]},
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request):
        """创建 BuildPack"""
        slz = BuildPackCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.BUILDPACK,
            attribute=slz.data["name"],
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=slz.data,
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

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
            target=OperationTarget.BUILDPACK,
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
            target=OperationTarget.BUILDPACK,
            attribute=buildpack.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SlugBuilderManageView(GenericTemplateView):
    name = "SlugBuilder 管理"
    template_name = "admin42/platformmgr/runtimes/slugbuilders.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["regions"] = list(get_all_regions().keys())
        context["image_types"] = dict(AppImageType.get_choices())
        context["step_meta_sets"] = {sms.id: str(sms) for sms in StepMetaSet.objects.all()}
        return context


class SlugBuilderAPIViewSet(GenericViewSet):
    """SlugBuilder 管理 API 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_bound_buildpacks(self, request, pk):
        """获取绑定和可绑定的 BuildPack 列表"""
        slugbuilder = AppSlugBuilder.objects.get(pk=pk)
        bound_buildpacks = slugbuilder.buildpacks.all()
        unbound_buildpacks = AppBuildPack.objects.exclude(id__in=bound_buildpacks)
        if slugbuilder.type == AppImageType.LEGACY:
            unbound_buildpacks = unbound_buildpacks.filter(type=BuildPackType.TAR)
        else:
            unbound_buildpacks = unbound_buildpacks.exclude(type=BuildPackType.TAR)

        return Response(
            {
                "bound_buildpacks": BuildPackListOutputSLZ(bound_buildpacks, many=True).data,
                "unbound_buildpacks": BuildPackListOutputSLZ(unbound_buildpacks, many=True).data,
            }
        )

    @transaction.atomic
    def set_bound_buildpacks(self, request, pk):
        """设置绑定 BuildPack 列表"""
        slugbuilder = AppSlugBuilder.objects.get(pk=pk)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data={"bound_buildpacks": [f"{bp.name}({bp.id})" for bp in slugbuilder.buildpacks.all()]},
        )
        slz = AppSlugBuilderBindInputSLZ(data=request.data, context={"slugbuilder_type": slugbuilder.type})
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        buildpacks = AppBuildPack.objects.filter(id__in=data["buildpack_ids"])
        binder = SlugbuilderBinder(slugbuilder=slugbuilder)
        binder.set_buildpacks(buildpacks)

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.SLUGBUILDER,
            attribute=slugbuilder.name,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data={"bound_buildpacks": [f"{bp.name}({bp.id})" for bp in buildpacks]},
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request):
        """获取 SlugBuilder 列表"""
        slugbuilders = AppSlugBuilder.objects.order_by("region")
        return Response(AppSlugBuilderListOutputSLZ(slugbuilders, many=True).data)

    def create(self, request):
        """创建 SlugBuilder"""
        slz = AppSlugBuilderCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.SLUGBUILDER,
            attribute=slz.data["name"],
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=slz.data,
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, pk):
        """更新 SlugBuilder"""
        slugbuilder = AppSlugBuilder.objects.get(pk=pk)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=AppSlugBuilderUpdateInputSLZ(slugbuilder).data,
        )

        slz = AppSlugBuilderUpdateInputSLZ(slugbuilder, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.SLUGBUILDER,
            attribute=slugbuilder.name,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=slz.data,
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk):
        """删除 SlugBuilder"""
        slugbuilder = AppSlugBuilder.objects.get(pk=pk)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=AppSlugBuilderListOutputSLZ(slugbuilder).data,
        )
        slugbuilder.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.SLUGBUILDER,
            attribute=slugbuilder.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
