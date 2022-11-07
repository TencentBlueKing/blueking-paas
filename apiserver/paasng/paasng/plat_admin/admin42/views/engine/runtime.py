# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging

from django.db import transaction
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.viewsets import GenericViewSet

from paasng.accounts.permissions.global_site import site_perm_required
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.serializers.runtime import AppBuildPackSLZ, AppSlugBuilderSLZ, AppSlugRunnerSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.helpers import ModuleRuntimeBinder, ModuleRuntimeManager
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.platform.modules.serializers import ModuleRuntimeBindSLZ

logger = logging.getLogger(__name__)


class ModuleRuntimeSLZ:
    def __init__(self, module):
        self.module = module
        self.mgr = ModuleRuntimeManager(module)

    def to_dict(self):
        try:
            return {
                "module": ModuleSLZ(self.module).data,
                "builder": AppSlugBuilderSLZ(self.mgr.get_slug_builder()).data,
                "runner": AppSlugRunnerSLZ(self.mgr.get_slug_runner()).data,
                "buildpacks": AppBuildPackSLZ(self.mgr.list_buildpacks(), many=True).data,
                "buildpack_ids": [item.id for item in self.mgr.list_buildpacks()],
            }
        except Exception:
            return {
                "module": ModuleSLZ(self.module).data,
                "builder": None,
                "runner": None,
                "buildpacks": [],
                "buildpack_ids": [],
            }


class RuntimeStack:
    def __init__(self, builder: AppSlugBuilder):
        self.builder = builder

    def to_dict(self):
        try:
            return {
                "builder": AppSlugBuilderSLZ(self.builder).data,
                "runner": AppSlugRunnerSLZ(
                    AppSlugRunner.objects.get(name=self.builder.name, region=self.builder.region)
                ).data,
                "buildpacks": AppBuildPackSLZ(self.builder.buildpacks, many=True).data,
            }
        except Exception:
            return None


class RuntimeManageView(ApplicationDetailBaseView):
    name = "运行时管理"
    template_name = "admin42/applications/detail/engine/runtime.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        kwargs["runtimes"] = [ModuleRuntimeSLZ(module).to_dict() for module in application.modules.all()]
        kwargs["stacks"] = list(
            filter(
                lambda item: item is not None,
                [
                    RuntimeStack(builder).to_dict()
                    for builder in AppSlugBuilder.objects.filter(region=application.region)
                ],
            )
        )
        kwargs["buildpacks"] = AppBuildPackSLZ(AppBuildPack.objects.filter(region=application.region), many=True).data
        return kwargs


class RuntimeManageViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """运行时管理 API"""

    schema = None

    def list(self, request, *args, **kwargs):
        application = self.get_application()
        return Response(ModuleRuntimeSLZ(module).to_dict() for module in application.modules.all())

    @site_perm_required("admin:read:application")
    @transaction.atomic
    def bind(self, request, **kwargs):
        """绑定运行时"""
        module = self.get_module_via_path()

        slz = ModuleRuntimeBindSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        image = slz.validated_data["image"]
        buildpack_ids = slz.validated_data["buildpacks_id"]
        slugbuilder = get_object_or_404(AppSlugBuilder.objects.filter_available(module), name=image)
        slugrunner = get_object_or_404(AppSlugRunner.objects.filter_available(module), name=image)

        buildpacks = slugbuilder.get_buildpack_choices(module, id__in=buildpack_ids)

        if len(buildpack_ids) != len(buildpacks):
            logger.error("some buildpack is missing, expect %s but got %d", buildpack_ids, buildpacks)
            raise Http404("some buildpack is missing")

        binder = ModuleRuntimeBinder(module)
        binder.clear_runtime()
        binder.bind_image(slugrunner, slugbuilder)

        orders = {bid: idx for idx, bid in enumerate(buildpack_ids)}
        buildpacks = sorted(buildpacks, key=lambda item: orders[item.id])
        binder.bind_buildpacks(buildpacks)
        return Response(status=HTTP_204_NO_CONTENT)
