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
from typing import Dict, List

from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from moby_distribution.registry.client import APIEndpoint, DockerRegistryV2Client
from moby_distribution.registry.resources.manifests import ManifestRef, ManifestSchema2
from moby_distribution.registry.utils import parse_image
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.applications.constants import ArtifactType
from paas_wl.platform.applications.models import Build, BuildProcess
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.engine import serializers
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


def get_app_docker_registry_client() -> DockerRegistryV2Client:
    return DockerRegistryV2Client.from_api_endpoint(
        api_endpoint=APIEndpoint(url=settings.APP_DOCKER_REGISTRY_HOST),
        username=settings.APP_DOCKER_REGISTRY_USERNAME,
        password=settings.APP_DOCKER_REGISTRY_PASSWORD,
    )


class ImageArtifactSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['status']
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
        build = get_object_or_404(Build.objects.filter(module_id=module.pk), uuid=build_id)
        image = parse_image(build.image, default_registry=settings.APP_DOCKER_REGISTRY_HOST)
        registry_client = get_app_docker_registry_client()
        ref = ManifestRef(repo=image.name, reference=image.tag, client=registry_client)
        metadata = ref.get_metadata()
        manifest: ManifestSchema2 = ref.get()

        # TODO: 构建记录
        build_records: List[Dict] = []
        # TODO: 部署记录
        deploy_records: List[Dict] = []
        return Response(
            data=serializers.ImageArtifactDetailSLZ(
                {
                    "repository": build.image_repository,
                    "tag": build.image_tag,
                    "size": sum(layer.size for layer in manifest.layers),
                    "digest": metadata.digest,
                    "invoke_message": build.build_process.invoke_message,
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
