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

from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.serializers.packages import SourcePackageSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.sourcectl.models import SourcePackage
from paasng.platform.sourcectl.package.downloader import download_package
from paasng.platform.sourcectl.utils import generate_temp_file


class SourcePackageManageView(ApplicationDetailBaseView):
    name = "包版本管理"
    template_name = "admin42/operation/applications/detail/engine/package.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        packages = SourcePackageSLZ(
            SourcePackage.objects.filter(module__in=application.modules.all()).order_by("module__is_default"),
            many=True,
        ).data
        kwargs["packages"] = packages
        kwargs["env_choices"] = [{"value": value, "text": text} for value, text in AppEnvName.get_choices()]
        kwargs["module_list"] = ModuleSLZ(application.modules.all(), many=True).data
        return kwargs


class SourcePackageManageViewSet(ListModelMixin, GenericViewSet):
    """包版本管理API"""

    schema = None
    queryset = SourcePackage.objects.all()
    serializer_class = SourcePackageSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_queryset(self):
        application = get_object_or_404(Application, code=self.kwargs["code"])
        # The "module_name" is optional in the path kwargs
        if module_name := self.kwargs.get("module_name"):
            module = application.get_module(module_name)
            return super().get_queryset().filter(module=module)
        else:
            return super().get_queryset().filter(module__application=application)

    def download(self, request, **kwargs):
        """下载已有源码包"""
        package = self.get_object()
        with generate_temp_file() as dest_path:
            download_package(package, dest_path=dest_path)
            content = dest_path.read_bytes()
        response = HttpResponse(content, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="bk_paas3_{package.package_name}"'
        return response
