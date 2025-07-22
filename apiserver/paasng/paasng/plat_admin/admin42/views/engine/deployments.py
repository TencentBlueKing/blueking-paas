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

from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.engine import DeploymentForListSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.models.deployment import Deployment


class DeploymentListView(GenericTemplateView):
    """查看当前应用部署数据"""

    name = "部署概览"
    serializer_class = DeploymentForListSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/operation/list_deployments.html"

    def get_queryset(self):
        queryset = Deployment.objects.all().order_by("-created").select_related("app_environment")
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        # Add extra properties
        for deployment in page:
            deployment.f_application_id = deployment.app_environment.module.application.code
            deployment.f_application_name = deployment.app_environment.module.application.name
            deployment.f_module_name = deployment.app_environment.module.name
            deployment.f_environment = deployment.app_environment.environment

        serializer = self.get_serializer(page or queryset, many=True)
        return serializer.data

    def get_context_data(self, **kwargs):
        self.paginator.default_limit = 10
        if "view" not in kwargs:
            kwargs["view"] = self

        data = self.list(self.request, *self.args, **self.kwargs)
        kwargs["deployment_list"] = data
        kwargs["pagination"] = self.get_pagination_context(self.request)
        return kwargs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
