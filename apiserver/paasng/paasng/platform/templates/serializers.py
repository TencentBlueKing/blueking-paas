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
from rest_framework import serializers

from paasng.platform.modules.serializers import (
    AppBuildPackMinimalSLZ,
    AppSlugBuilderMinimalSLZ,
    ImageTagOptionsSLZ,
    RuntimeType,
)
from paasng.utils.i18n.serializers import TranslatedCharField


class SearchTemplateSLZ(serializers.Serializer):
    """获取可用模板列表"""

    region = serializers.CharField(required=True, max_length=16, help_text="应用版本")
    tags = serializers.CharField(required=False, max_length=128, default="", help_text="标签，多个则以英文逗号拼接")
    fuzzy_name = serializers.CharField(required=False, max_length=64, help_text="名称（模糊匹配）")

    def validate_tags(self, tags):
        # 转换成 Set 类型
        return {t for t in tags.split(",") if t}


class TemplateSLZ(serializers.Serializer):
    """模板数据"""

    name = serializers.CharField()
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    tags = serializers.JSONField()
    region = serializers.SerializerMethodField()
    repo_url = serializers.CharField()

    def get_region(self, tmpl):
        return tmpl.enabled_regions


class BuildConfigPreviewSLZ(serializers.Serializer):
    """构建配置预览"""

    image_repository_template = serializers.CharField(help_text="镜像仓库模板", read_only=True)
    build_method = serializers.ChoiceField(help_text="构建方式", choices=RuntimeType.get_choices(), required=True)
    tag_options = ImageTagOptionsSLZ(help_text="镜像 Tag 规则", required=False)

    # buildpack build 相关字段
    bp_stack_name = serializers.CharField(help_text="buildpack 构建方案的基础镜像名", allow_null=True, required=False)
    buildpacks = serializers.ListField(child=AppBuildPackMinimalSLZ(), allow_null=True, required=False)

    # docker build 相关字段
    dockerfile_path = serializers.CharField(help_text="Dockerfile 路径", allow_null=True, required=False)
    docker_build_args = serializers.DictField(
        child=serializers.CharField(allow_blank=False), allow_empty=True, allow_null=True, required=False
    )


class TemplateDetailSLZ(serializers.Serializer):
    """模板详情"""

    slugbuilder = AppSlugBuilderMinimalSLZ(help_text="基础镜像详细信息")
    build_config = BuildConfigPreviewSLZ()
