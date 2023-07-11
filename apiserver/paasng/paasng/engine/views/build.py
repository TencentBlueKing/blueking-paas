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

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.applications.constants import ArtifactType
from paas_wl.platform.applications.models import Build, BuildProcess
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.engine import serializers
from paasng.engine.constants import JobStatus
from paasng.engine.models import Deployment
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class ImageArtifactViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['image']
    ordering = ('-created',)

    @swagger_auto_schema(response_serializer=serializers.ImageArtifactMinimalSLZ(many=True))
    def list_image(self, request, code, module_name):
        """获取镜像类型的构件列表"""
        module = self.get_module_via_path()
        qs = self.filter_queryset(
            Build.objects.filter(
                module_id=module.pk, artifact_type=ArtifactType.IMAGE, artifact_deleted=False
            ).select_related("build_process")
        )
        page = self.paginate_queryset(qs)
        serializer = serializers.ImageArtifactMinimalSLZ(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(response_serializer=serializers.ImageArtifactDetailSLZ)
    def retrieve_image_detail(self, request, code, module_name, build_id):
        """获取镜像构件的详情"""
        module = self.get_module_via_path()
        build = get_object_or_404(Build.objects.filter(module_id=module.pk, artifact_deleted=False), uuid=build_id)

        build_records = Build.objects.filter(
            module_id=module.pk, artifact_type=ArtifactType.IMAGE, image=build.image
        ).order_by("-created")
        deploy_records = []
        for deploy in (
            Deployment.objects.owned_by_module(module)
            .filter(build_id=build.uuid, status=JobStatus.SUCCESSFUL)
            .order_by("-created")
        ):
            deploy_records.append(
                {
                    "operator": deploy.operator,
                    "environment": deploy.app_environment.environment,
                    "at": deploy.complete_time,
                }
            )
        return Response(
            data=serializers.ImageArtifactDetailSLZ(
                {
                    "image_info": build,
                    "build_records": build_records,
                    "deploy_records": deploy_records,
                }
            ).data
        )


class BuildProcessViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['status']
    ordering = ('-created',)

    @swagger_auto_schema(response_serializer=serializers.BuildProcessSLZ(many=True))
    def list(self, request, code, module_name):
        """获取构建历史"""
        module = self.get_module_via_path()
        qs = self.filter_queryset(BuildProcess.objects.filter(module_id=module.pk).select_related("build"))
        page = self.paginate_queryset(qs)
        serializer = serializers.BuildProcessSLZ(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)
