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

from rest_framework import serializers

from paasng.utils.i18n.serializers import TranslatedCharField


class SearchTemplateSLZ(serializers.Serializer):
    """获取可用模板列表"""

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
    repo_url = serializers.CharField()
    language = serializers.CharField()


class TemplateRenderOutputSLZ(serializers.Serializer):
    """模板渲染信息"""

    name = serializers.CharField(help_text="模板名称")
    display_name = TranslatedCharField()
    description = TranslatedCharField()
    repo_url = serializers.CharField(help_text="代码仓库地址")
    render_method = serializers.CharField(help_text="模版代码渲染方式")
    source_dir = serializers.CharField(help_text="模板代码所在相对目录", source="get_source_dir")
