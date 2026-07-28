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

from typing import TYPE_CHECKING

from rest_framework import serializers

if TYPE_CHECKING:
    from paasng.platform.agent_sandbox.models import ImageBuildRecord
    from paasng.platform.sandbox_instance.models import SidecarImage


class SidecarImageBuildInputSLZ(serializers.Serializer):
    """通过 Kaniko 构建创建 sidecar 镜像"""

    source_url = serializers.URLField(label="源码压缩包 URL", max_length=1024)
    image_name = serializers.CharField(label="目标镜像名称", max_length=256)
    image_tag = serializers.CharField(label="目标镜像标签", max_length=128)
    dockerfile_path = serializers.CharField(label="Dockerfile 相对路径", max_length=512, default="Dockerfile")
    docker_build_args = serializers.DictField(
        label="Docker 构建参数", child=serializers.CharField(), required=False, default=dict
    )


class SidecarImageBuildOutputSLZ(serializers.Serializer):
    """构建请求返回"""

    build_id = serializers.UUIDField(source="uuid")


class SidecarImageRegisterInputSLZ(serializers.Serializer):
    """直接注册已有 sidecar 镜像"""

    image = serializers.CharField(label="完整镜像地址", max_length=512)
    name = serializers.CharField(label="镜像名称", max_length=256)
    tag = serializers.CharField(label="镜像标签", max_length=128)


class SidecarImageOutputSLZ(serializers.Serializer):
    """Sidecar 镜像信息输出"""

    id = serializers.UUIDField(source="uuid")
    image = serializers.CharField()
    name = serializers.CharField()
    tag = serializers.CharField()
    build_id = serializers.SerializerMethodField()
    created = serializers.DateTimeField()

    def get_build_id(self, obj: "SidecarImage") -> str | None:
        if obj.build_record_id:
            return str(obj.build_record_id)
        return None


class SidecarImageBuildStatusSLZ(serializers.Serializer):
    """构建状态查询输出"""

    build_id = serializers.UUIDField(source="uuid")
    status = serializers.CharField()
    output_image = serializers.CharField(help_text="完整的输出镜像地址")
    build_logs = serializers.SerializerMethodField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()

    def get_build_logs(self, obj: "ImageBuildRecord") -> str:
        if not obj.completed_at:
            return f"Building image {obj.output_image} ..."
        return obj.log.content


class SidecarImageQuerySLZ(serializers.Serializer):
    """查询可用 sidecar 镜像列表的过滤参数"""

    name = serializers.CharField(label="镜像名称", required=False)
    tag = serializers.CharField(label="镜像标签", required=False)
