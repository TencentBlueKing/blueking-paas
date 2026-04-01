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

from typing import TYPE_CHECKING

from rest_framework import serializers

if TYPE_CHECKING:
    from paasng.platform.agent_sandbox.models import ImageBuildRecord


class ImageBuildCreateInputSLZ(serializers.Serializer):
    source_url = serializers.URLField(label="源码压缩包 URL", max_length=1024)
    image_name = serializers.CharField(label="目标镜像名称", max_length=256)
    image_tag = serializers.CharField(label="目标镜像标签", max_length=128)
    dockerfile_path = serializers.CharField(label="Dockerfile 相对路径", max_length=512, default="Dockerfile")
    docker_build_args = serializers.DictField(
        label="Docker 构建参数", child=serializers.CharField(), required=False, default=dict
    )


class ImageBuildCreateOutputSLZ(serializers.Serializer):
    build_id = serializers.UUIDField(source="uuid")


class ImageBuildQuerySLZ(serializers.Serializer):
    image_name = serializers.CharField(label="镜像名称", required=False)
    image_tag = serializers.CharField(label="镜像标签", required=False)


class ImageBuildResultSLZ(serializers.Serializer):
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
