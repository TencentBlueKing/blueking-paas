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

from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.sourcectl.source_types import get_sourcectl_types
from paasng.platform.templates.constants import RenderMethod, TemplateType
from paasng.platform.templates.models import Template


class TemplateMinimalOutputSLZ(serializers.Serializer):
    """模板最小化序列化器"""

    id = serializers.CharField(help_text="模板 ID")
    name = serializers.CharField(help_text="模板名称")
    display_name_zh_cn = serializers.CharField(help_text="模板中文名称")
    display_name_en = serializers.CharField(help_text="模板英文名称")
    type = serializers.CharField(help_text="模板类型")
    language = serializers.CharField(help_text="开发语言")
    is_display = serializers.SerializerMethodField(help_text="是否显示")

    def get_is_display(self, obj: Template) -> bool:
        """获取模板是否显示"""
        return not obj.is_hidden


class TemplateDetailOutputSLZ(serializers.Serializer):
    """模板详情序列化器"""

    # 基本信息
    name = serializers.CharField(help_text="模板名称")
    type = serializers.CharField(help_text="模板类型")
    render_method = serializers.CharField(help_text="模板代码渲染方式")
    display_name_zh_cn = serializers.CharField(help_text="模板中文名称")
    display_name_en = serializers.CharField(help_text="模板英文名称")
    description_zh_cn = serializers.CharField(help_text="模板中文描述")
    description_en = serializers.CharField(help_text="模板英文描述")
    language = serializers.CharField(help_text="开发语言")
    is_display = serializers.SerializerMethodField(help_text="是否显示")
    # 模板信息
    blob_url = serializers.JSONField(help_text="二进制包存储路径")
    repo_type = serializers.CharField(help_text="代码仓库类型")
    repo_url = serializers.CharField(help_text="代码仓库地址")
    source_dir = serializers.CharField(help_text="模板代码所在目录")
    # 配置信息
    preset_services_config = serializers.JSONField(help_text="预设增强服务配置")
    required_buildpacks = serializers.JSONField(help_text="必须的构建工具")
    processes = serializers.JSONField(help_text="进程配置")
    market_ready = serializers.BooleanField(help_text="是否已准备好在市场中展示")

    def get_is_display(self, obj: Template) -> bool:
        """获取模板是否显示"""
        return not obj.is_hidden


class TemplateBaseInputSLZ(serializers.Serializer):
    """模板基础输入序列化器"""

    # 基本信息
    name = serializers.CharField(help_text="模板名称", max_length=64)
    type = serializers.ChoiceField(help_text="模板类型", choices=TemplateType.get_django_choices())
    render_method = serializers.ChoiceField(help_text="模板代码渲染方式", choices=RenderMethod.get_django_choices())
    display_name_zh_cn = serializers.CharField(help_text="模板中文名称", max_length=64)
    display_name_en = serializers.CharField(help_text="模板英文名称", max_length=64)
    description_zh_cn = serializers.CharField(help_text="模板中文描述", max_length=128)
    description_en = serializers.CharField(help_text="模板英文描述", max_length=128)
    language = serializers.ChoiceField(help_text="开发语言", choices=AppLanguage.get_django_choices())
    is_display = serializers.BooleanField(help_text="是否显示")
    # 模板信息
    ## TemplateType.NORMAL 独有的信息
    blob_url = serializers.JSONField(help_text="二进制包存储路径", default=dict)
    ## TemplateType.PLUGIN 独有的信息
    repo_type = serializers.CharField(help_text="代码仓库类型", allow_blank=True, default="")
    repo_url = serializers.CharField(help_text="代码仓库地址", max_length=256, allow_blank=True, default="")
    source_dir = serializers.CharField(help_text="模板代码所在目录", allow_blank=True, default="")

    # 配置信息
    preset_services_config = serializers.JSONField(help_text="预设增强服务配置", default=dict)
    required_buildpacks = serializers.JSONField(help_text="必须的构建工具", default=list)
    processes = serializers.JSONField(help_text="进程配置", default=dict)
    market_ready = serializers.BooleanField(help_text="是否可发布到应用市集", default=False)

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)

        # 处理 is_display 字段，将其转换为数据库中存储的 is_hidden
        validated_data["is_hidden"] = not validated_data.pop("is_display")
        return validated_data

    def validate_repo_type(self, value: str) -> str:
        """验证代码仓库类型"""
        repo_types = [item[0] for item in get_sourcectl_types().get_choices()]
        if value and value not in repo_types:
            raise ValidationError(_("不支持的代码仓库类型"))
        return value

    def validate_preset_services_config(self, conf: Dict) -> Dict:
        if not isinstance(conf, dict):
            raise ValidationError(_("预设增强服务配置必须为 Dict 格式"))
        return conf

    def validate_required_buildpacks(self, required_buildpacks: Union[List, Dict]) -> Union[List, Dict]:
        if isinstance(required_buildpacks, list):
            if any(not isinstance(bp, str) for bp in required_buildpacks):
                raise ValidationError(_("构建工具配置必须为 List[str] 格式"))
        elif isinstance(required_buildpacks, dict):
            if "__default__" not in required_buildpacks:
                raise ValidationError(_("针对不同镜像配置 required_buildpacks 时必须配置默认值 __default__"))
            for required_buildpacks_for_image in required_buildpacks.values():
                if any(not isinstance(bp, str) for bp in required_buildpacks_for_image):
                    raise ValidationError(_("构建工具配置必须为 Dict[str, List[str]] 格式"))
        else:
            raise ValidationError(_("构建工具必须为 List[str] 或 Dict[str, List[str]] 格式"))
        return required_buildpacks

    def validate_processes(self, processes: Dict) -> Dict:
        if not isinstance(processes, dict):
            raise ValidationError(_("进程配置必须为 Dict 格式"))
        return processes

    def validate(self, attrs: Dict) -> Dict:
        """根据特定字段验证其他相应字段"""

        # 隐藏模板时不做严格验证
        if attrs.get("is_hidden", True):
            return attrs

        template_type = attrs["type"]

        # 普通应用模板验证
        if template_type == TemplateType.NORMAL:
            # 确保插件模板独有字段为默认值, 空字符串
            for field, default in [("repo_type", ""), ("repo_url", ""), ("source_dir", "")]:
                if attrs.get(field) != default:
                    attrs[field] = default
            # blob_url 必须有值
            if not attrs.get("blob_url"):
                raise ValidationError(_("二进制包存储配置必须为有效的地址字符串"))

        # 插件模板验证
        elif template_type == TemplateType.PLUGIN:
            # 验证插件模板必填字段
            if not attrs.get("repo_url"):
                raise ValidationError({"repo_url": _("插件模板必须配置代码仓库地址")})
            if not attrs.get("source_dir"):
                raise ValidationError({"source_dir": _("插件模板必须配置代码所在目录")})

            # 确保普通应用模板独有字段为默认值
            if attrs.get("blob_url") != {}:
                attrs["blob_url"] = {}

        return attrs


class TemplateCreateInputSLZ(TemplateBaseInputSLZ):
    """模板更新输入序列化器"""

    def validate_name(self, name: str) -> str:
        """验证模板名称唯一性"""
        if Template.objects.filter(name=name).exists():
            raise ValidationError(_("名称已存在，请使用其他名称"))
        return name


class TemplateUpdateInputSLZ(TemplateBaseInputSLZ):
    """模板更新输入序列化器"""

    def validate_name(self, name: str) -> str:
        """验证模板名称唯一性（更新时排除自身）"""
        # 获取当前更新的实例
        instance = self.context.get("instance")

        queryset = Template.objects.filter(name=name).exclude(id=instance.id)

        if queryset.exists():
            raise ValidationError(_("名称已存在，请使用其他名称"))
        return name
