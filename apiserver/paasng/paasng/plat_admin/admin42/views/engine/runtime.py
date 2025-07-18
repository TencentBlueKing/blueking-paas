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

import logging

from django.db import transaction
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.viewsets import GenericViewSet

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.serializers.runtime import AppBuildPackSLZ, AppSlugBuilderSLZ, AppSlugRunnerSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.models import Application
from paasng.platform.modules.exceptions import BPNotFound
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
                # name 要唯一
                "runner": AppSlugRunnerSLZ(AppSlugRunner.objects.get(name=self.builder.name)).data,
                "buildpacks": AppBuildPackSLZ(self.builder.buildpacks, many=True).data,
            }
        except Exception:
            return None


class RuntimeManageView(ApplicationDetailBaseView):
    name = "运行时管理"
    template_name = "admin42/operation/applications/detail/engine/runtime.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        kwargs["runtimes"] = [ModuleRuntimeSLZ(module).to_dict() for module in application.modules.all()]
        kwargs["stacks"] = list(
            filter(
                lambda item: item is not None,
                [RuntimeStack(builder).to_dict() for builder in AppSlugBuilder.objects.all()],
            )
        )
        kwargs["buildpacks"] = AppBuildPackSLZ(AppBuildPack.objects.all(), many=True).data
        return kwargs


class RuntimeManageViewSet(GenericViewSet):
    """运行时管理 API"""

    schema = None
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, *args, **kwargs):
        application = get_object_or_404(Application, code=kwargs["code"])
        return Response(ModuleRuntimeSLZ(module).to_dict() for module in application.modules.all())

    @transaction.atomic
    def bind(self, request, **kwargs):
        """绑定运行时"""
        application = get_object_or_404(Application, code=kwargs["code"])
        module = application.get_module(kwargs["module_name"])

        slz = ModuleRuntimeBindSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        bp_stack_name = slz.validated_data["image"]
        buildpack_ids = slz.validated_data["buildpacks_id"]
        try:
            binder = ModuleRuntimeBinder(module)
            binder.bind_bp_stack(bp_stack_name, buildpack_ids)
        except BPNotFound:
            raise Http404("some buildpack is missing")
        return Response(status=HTTP_204_NO_CONTENT)
