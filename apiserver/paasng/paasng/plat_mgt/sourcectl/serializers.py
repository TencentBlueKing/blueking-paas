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


from typing import Dict

from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.sourcectl.models import SourceTypeSpecConfig


class BaseSourceTypeSpecConfigSLZ(serializers.Serializer):
    """基础代码库配置 SLZ

    包含代码库配置的所有基础字段定义
    """

    # === 基础配置字段 ===
    name = serializers.CharField(help_text="服务名称")
    label_zh_cn = serializers.CharField(help_text="中文标签")
    label_en = serializers.CharField(help_text="英文标签")
    enabled = serializers.BooleanField(help_text="是否启用")
    spec_cls = serializers.CharField(help_text="配置类路径")
    server_config = serializers.JSONField(help_text="服务配置")

    # === OAuth 配置字段 ===
    authorization_base_url = serializers.CharField(help_text="OAuth 授权链接", allow_blank=True)
    client_id = serializers.CharField(help_text="OAuth App Client ID", allow_blank=True)
    client_secret = serializers.CharField(help_text="OAuth App Client Secret", allow_blank=True)
    redirect_uri = serializers.CharField(help_text="OAuth 回调地址", allow_blank=True)
    token_base_url = serializers.CharField(help_text="OAuth 获取 Token 链接", allow_blank=True)
    oauth_display_info_zh_cn = serializers.JSONField(help_text="OAuth 展示信息（中文）")
    oauth_display_info_en = serializers.JSONField(help_text="OAuth 展示信息（英文）")

    # === 展示信息字段 ===
    display_info_zh_cn = serializers.JSONField(help_text="中文展示信息")
    display_info_en = serializers.JSONField(help_text="英文展示信息")

    def to_internal_value(self, data):
        # 添加前缀 paasng.platform.sourcectl.type_specs.
        prefix = "paasng.platform.sourcectl.type_specs."
        data = super().to_internal_value(data)

        data["spec_cls"] = prefix + data["spec_cls"]
        return data

    def to_representation(self, instance):
        # 将 spec_cls 字段转换为可读格式
        data = super().to_representation(instance)
        data["spec_cls"] = data["spec_cls"].rsplit(".", 1)[-1]
        return data


# ===== 输出序列化器 =====


class SourceTypeSpecConfigMinimalOutputSLZ(serializers.Serializer):
    """代码库配置最小化输出序列化器

    用于列表展示，只包含必要字段
    """

    id = serializers.IntegerField(help_text="配置 ID")
    name = serializers.CharField(help_text="服务名称")
    label_zh_cn = serializers.CharField(help_text="中文标签")
    label_en = serializers.CharField(help_text="英文标签")
    enabled = serializers.BooleanField(help_text="是否启用")
    client_id = serializers.CharField(help_text="OAuth Client ID")


class SourceTypeSpecConfigDetailOutputSLZ(BaseSourceTypeSpecConfigSLZ):
    """代码库配置详情输出序列化器

    用于详情展示，包含所有字段
    """


# ===== 输入序列化器 =====


class BaseSourceTypeSpecConfigInputSLZ(BaseSourceTypeSpecConfigSLZ):
    """代码库配置基础输入序列化器

    包含输入验证的通用逻辑
    """

    # === 验证方法 ===
    def validate_server_config(self, conf: Dict) -> Dict:
        if not isinstance(conf, dict):
            raise ValidationError(_("服务配置格式必须为 Dict"))
        return conf

    def validate_display_info_zh_cn(self, display_info: Dict) -> Dict:
        return self._validate_display_info(display_info)

    def validate_display_info_en(self, display_info: Dict) -> Dict:
        return self._validate_display_info(display_info)

    def validate_oauth_display_info_zh_cn(self, display_info: Dict) -> Dict:
        return self._validate_oauth_display_info(display_info)

    def validate_oauth_display_info_en(self, display_info: Dict) -> Dict:
        return self._validate_oauth_display_info(display_info)

    def validate(self, attrs: Dict) -> Dict:
        # 尝试使用配置初始化 SourceTypeSpec 以校验配置的合法性
        conf = SourceTypeSpecConfig(**attrs).to_dict()
        try:
            cls = import_string(attrs["spec_cls"])
        except ImportError:
            raise ValidationError(_("配置类路径有误，导入失败"))

        try:
            source_type_spec = cls(**conf["attrs"])
        except Exception as e:
            raise ValidationError(_("初始化 SourceTypeSpec 失败：{}").format(str(e)))

        if not source_type_spec.support_oauth():
            return attrs

        # 如果使用了支持 OAuth 配置的配置类，则必须填写相关字段
        oauth_fields_map = {
            "authorization_base_url": _("OAuth 授权链接"),
            "client_id": "ClientID",
            "client_secret": "ClientSecret",
            "redirect_uri": _("回调地址"),
            "token_base_url": _("获取 Token 链接"),
            "oauth_display_info_en": _("OAuth 展示信息（英）"),
            "oauth_display_info_zh_cn": _("OAuth 展示信息（中）"),
        }
        for field, title in oauth_fields_map.items():
            if not attrs.get(field):
                raise ValidationError(_("使用配置类 {} 时，字段 {} 不可为空").format(cls.__name__, title))

        return attrs

    @staticmethod
    def _validate_display_info(display_info: Dict) -> Dict:
        if not isinstance(display_info, dict):
            raise ValidationError(_("展示信息格式必须为 Dict"))

        # 如果填写 display_info，则必须包含键 name，description
        if display_info and not ("name" in display_info and "description" in display_info):
            raise ValidationError(_("展示信息有误，非空则必须包含 name，description 键"))

        available_fields = {"name", "description"}
        if unsupported_fields := display_info.keys() - available_fields:
            raise ValidationError(_("展示信息不支持字段 {}").format(unsupported_fields))

        return display_info

    @staticmethod
    def _validate_oauth_display_info(display_info: Dict) -> Dict:
        if not isinstance(display_info, dict):
            raise ValidationError(_("OAuth 展示信息格式必须为 Dict"))

        available_fields = {"icon", "display_name", "address", "description", "auth_docs"}
        if unsupported_fields := display_info.keys() - available_fields:
            raise ValidationError(_("OAuth 展示信息不支持字段 {}").format(unsupported_fields))

        return display_info


class SourceTypeSpecConfigCreateInputSLZ(BaseSourceTypeSpecConfigInputSLZ):
    """创建代码库配置输入 SLZ"""

    def validate_name(self, name: str) -> str:
        """代码库配置名称唯一性"""
        if SourceTypeSpecConfig.objects.filter(name=name).exists():
            raise ValidationError(_("名称已存在，请使用其他名称"))
        return name


class SourceTypeSpecConfigUpdateInputSLZ(BaseSourceTypeSpecConfigInputSLZ):
    """更新代码库配置的 SLZ"""

    def validate_name(self, name: str) -> str:
        """验证代码库名称唯一性（更新时排除自身）"""
        # 获取当前更新的实例
        instance = self.context.get("instance")

        if SourceTypeSpecConfig.objects.filter(name=name).exclude(id=instance.id).exists():
            raise ValidationError(_("名称已存在，请使用其他名称"))
        return name
