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
from django.http.response import HttpResponse
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from paasng.accounts.permissions.global_site import site_perm_required
from paasng.dev_resources.sourcectl.models import SourcePackage
from paasng.dev_resources.sourcectl.package.downloader import download_package
from paasng.dev_resources.sourcectl.utils import generate_temp_file
from paasng.engine.constants import AppEnvName
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.serializers.packages import SourcePackageSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin


class SourcePackageManageView(ApplicationDetailBaseView):
    name = "包版本管理"
    template_name = "admin42/applications/detail/engine/package.html"

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


class SourcePackageManageViewSet(ListModelMixin, GenericViewSet, ApplicationCodeInPathMixin):
    """包版本管理API"""

    schema = None
    queryset = SourcePackage.objects.all()
    serializer_class = SourcePackageSLZ

    def get_queryset(self):
        application = self.get_application()
        try:
            module = self.get_module_via_path()
        except ValueError:
            return super().get_queryset().filter(module__application=application)
        return super().get_queryset().filter(module=module)

    @site_perm_required("admin:read:application")
    def download(self, request, **kwargs):
        """下载已有源码包"""
        package = self.get_object()
        with generate_temp_file() as dest_path:
            download_package(package, dest_path=dest_path)
            content = dest_path.read_bytes()
        response = HttpResponse(content, content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="bk_paas3_{package.package_name}"'
        return response
