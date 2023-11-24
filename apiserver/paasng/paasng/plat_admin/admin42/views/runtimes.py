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
from typing import Type

from django.db import transaction
from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.viewsets import ModelViewSet

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.runtime import (
    AppBuildPackSLZ,
    AppSlugBuilderSLZ,
    AppSlugRunnerSLZ,
    SlugBuilderBindRequest,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
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
        return Response(status=HTTP_204_NO_CONTENT)


slugrunner_generator = RuntimeAdminViewGenerator(
    name="SlugRunner管理",
    template_name="admin42/platformmgr/runtime/slugrunner_list.html",
    serializer_class=AppSlugRunnerSLZ,
    queryset=AppSlugRunner.objects.order_by("region"),
)

SlugRunnerTemplateView = slugrunner_generator.gen_template_view()
SlugRunnerAPIViewSet = slugrunner_generator.gen_model_view_set()
