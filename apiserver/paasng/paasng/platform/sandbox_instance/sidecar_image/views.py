# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from paasng.platform.agent_sandbox.image_build.constants import ImageType
from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.platform.sandbox_instance.models import SidecarImage
from paasng.platform.sandbox_instance.sidecar_image.serializers import (
    SidecarImageBuildInputSLZ,
    SidecarImageBuildOutputSLZ,
    SidecarImageBuildStatusSLZ,
    SidecarImageOutputSLZ,
    SidecarImageQuerySLZ,
    SidecarImageRegisterInputSLZ,
)
from paasng.platform.sandbox_instance.sidecar_image.tasks import run_sidecar_image_build

logger = logging.getLogger(__name__)


@ForceAllowAuthedApp.mark_view_set
class SidecarImageViewSet(viewsets.ViewSet):
    """Sidecar 镜像管理接口（System API）。

    为 SandboxInstance 类型的 AI Agent 应用提供 sidecar 容器镜像的构建、注册和查询能力。
    """

    permission_classes = [sysapi_client_perm_class(ClientAction.MANAGE_SIDECAR_IMAGE)]

    @swagger_auto_schema(
        tags=["sidecar_image"],
        request_body=SidecarImageBuildInputSLZ(),
        responses={status.HTTP_201_CREATED: SidecarImageBuildOutputSLZ()},
    )
    def build(self, request):
        """提交 sidecar 镜像构建请求，异步执行 Kaniko 构建并返回构建 ID。

        构建成功后会自动注册为可用的 sidecar 镜像。
        """
        slz = SidecarImageBuildInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        build = ImageBuildRecord.objects.create(
            app_code=request.app.bk_app_code,
            source_url=data["source_url"],
            image_name=data["image_name"],
            image_tag=data["image_tag"],
            dockerfile_path=data["dockerfile_path"],
            docker_build_args=data["docker_build_args"],
            image_type=ImageType.SIDECAR.value,
            tenant_id=request.app.tenant_id or get_init_tenant_id(),
        )

        run_sidecar_image_build.delay(str(build.uuid))

        return Response(SidecarImageBuildOutputSLZ(build).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["sidecar_image"],
        responses={status.HTTP_200_OK: SidecarImageBuildStatusSLZ()},
    )
    def build_status(self, request, build_id):
        """按构建 ID 查询 sidecar 镜像构建状态。"""
        build = get_object_or_404(
            ImageBuildRecord,
            uuid=build_id,
            app_code=request.app.bk_app_code,
            image_type=ImageType.SIDECAR.value,
            tenant_id=request.app.tenant_id or get_init_tenant_id(),
        )
        return Response(SidecarImageBuildStatusSLZ(build).data)

    @swagger_auto_schema(
        tags=["sidecar_image"],
        request_body=SidecarImageRegisterInputSLZ(),
        responses={status.HTTP_201_CREATED: SidecarImageOutputSLZ()},
    )
    def register(self, request):
        """直接注册一个已有镜像为 sidecar 可用镜像（不走构建流程）。"""
        slz = SidecarImageRegisterInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        tenant_id = request.app.tenant_id or get_init_tenant_id()
        sidecar_image, _ = SidecarImage.objects.get_or_create(
            app_code=request.app.bk_app_code,
            image=data["image"],
            tenant_id=tenant_id,
            defaults={
                "name": data["name"],
                "tag": data["tag"],
            },
        )

        return Response(SidecarImageOutputSLZ(sidecar_image).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["sidecar_image"],
        query_serializer=SidecarImageQuerySLZ(),
        responses={status.HTTP_200_OK: SidecarImageOutputSLZ(many=True)},
    )
    def list(self, request):
        """查询可用 sidecar 镜像列表，支持按 name/tag 过滤。"""
        slz = SidecarImageQuerySLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        queryset = SidecarImage.objects.filter(
            app_code=request.app.bk_app_code,
            tenant_id=request.app.tenant_id or get_init_tenant_id(),
        )
        if name := data.get("name"):
            queryset = queryset.filter(name=name)
        if tag := data.get("tag"):
            queryset = queryset.filter(tag=tag)

        return Response(SidecarImageOutputSLZ(queryset, many=True).data)

    @swagger_auto_schema(
        tags=["sidecar_image"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, image_id):
        """删除一条 sidecar 镜像记录。"""
        sidecar_image = get_object_or_404(
            SidecarImage,
            uuid=image_id,
            app_code=request.app.bk_app_code,
            tenant_id=request.app.tenant_id or get_init_tenant_id(),
        )
        sidecar_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
