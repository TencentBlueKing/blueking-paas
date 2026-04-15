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

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.platform.agent_sandbox.image_build.serializers import (
    ImageBuildCreateInputSLZ,
    ImageBuildCreateOutputSLZ,
    ImageBuildQuerySLZ,
    ImageBuildResultSLZ,
)
from paasng.platform.agent_sandbox.image_build.tasks import run_image_build
from paasng.platform.agent_sandbox.models import ImageBuildRecord

logger = logging.getLogger(__name__)


@ForceAllowAuthedApp.mark_view_set
class ImageBuildViewSet(viewsets.ViewSet):
    """Agent Sandbox 镜像构建相关接口（System API）。"""

    permission_classes = [sysapi_client_perm_class(ClientAction.BUILD_SANDBOX_IMAGE)]

    @swagger_auto_schema(
        tags=["image_build"],
        request_body=ImageBuildCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: ImageBuildCreateOutputSLZ()},
    )
    def create(self, request):
        """创建镜像构建任务，异步执行构建并返回构建 ID。"""
        slz = ImageBuildCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        build = ImageBuildRecord.objects.create(
            app_code=request.app.bk_app_code,
            source_url=data["source_url"],
            image_name=data["image_name"],
            image_tag=data["image_tag"],
            dockerfile_path=data["dockerfile_path"],
            docker_build_args=data["docker_build_args"],
            tenant_id=request.app.tenant_id or get_init_tenant_id(),
        )

        run_image_build.delay(str(build.uuid), pre_pull=data["pre_pull"])

        return Response(ImageBuildCreateOutputSLZ(build).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["image_build"],
        responses={status.HTTP_200_OK: ImageBuildResultSLZ()},
    )
    def retrieve(self, request, build_id):
        """按构建 ID 查询构建结果。"""
        build = get_object_or_404(ImageBuildRecord, uuid=build_id, app_code=request.app.bk_app_code)
        return Response(ImageBuildResultSLZ(build).data)

    @swagger_auto_schema(
        tags=["image_build"],
        query_serializer=ImageBuildQuerySLZ(),
        responses={status.HTTP_200_OK: ImageBuildResultSLZ(many=True)},
    )
    def list(self, request):
        """按 image_name 和 image_tag 查询构建记录，按 started_at 降序排列。"""
        slz = ImageBuildQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        queryset = ImageBuildRecord.objects.filter(app_code=request.app.bk_app_code)
        if image_name := data.get("image_name"):
            queryset = queryset.filter(image_name=image_name)
        if image_tag := data.get("image_tag"):
            queryset = queryset.filter(image_tag=image_tag)

        queryset = queryset.order_by("-started_at")
        return Response(ImageBuildResultSLZ(queryset, many=True).data)
