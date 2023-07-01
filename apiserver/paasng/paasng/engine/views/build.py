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
import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from paas_wl.platform.applications.models import BuildProcess
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.engine.serializers import BuildProcessSLZ
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class BuildProcessViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    serializer_class = BuildProcessSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['status']
    ordering = ('-created',)

    @swagger_auto_schema(response_serializer=BuildProcessSLZ(many=True))
    def list(self, request, code, module_name, environment):
        """获取构建历史"""
        wl_app = self.get_wl_app_via_path()
        qs = self.filter_queryset(BuildProcess.objects.filter(app=wl_app).select_related("build"))
        page = self.paginate_queryset(qs)
        serializer = BuildProcessSLZ(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)
