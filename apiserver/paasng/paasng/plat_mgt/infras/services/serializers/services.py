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
import re

from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.servicehub.constants import ServiceType
from paasng.accessories.servicehub.local.manager import LocalServiceObj
from paasng.accessories.servicehub.remote.manager import RemoteServiceObj
from paasng.utils.i18n import to_translated_field

# 增强服务名称规范
ADDONS_SERVICE_NAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,30}[a-zA-Z0-9]$")


class ServiceObjOutputSLZ(serializers.Serializer):
    """增强服务详情"""

    uuid = serializers.CharField(help_text="唯一 ID")
    name = serializers.CharField(help_text="名称")
    category_id = serializers.IntegerField(help_text="服务分类")
    display_name = serializers.CharField(help_text="展示用名称")
    logo = serializers.CharField()

    description = serializers.CharField(help_text="描述")
    long_description = serializers.CharField(help_text="详细描述")
    instance_tutorial = serializers.CharField(help_text="服务 markdown 描述")
    config = serializers.JSONField(required=False, default=dict)
    plan_schema = serializers.JSONField(required=False, default=dict)

    is_visible = serializers.BooleanField(help_text="是否可见")

    provider_name = serializers.CharField(help_text="供应商", required=False, allow_null=True, allow_blank=True)
    origin = serializers.SerializerMethodField(help_text="服务来源")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_origin(self, obj) -> str:
        if isinstance(obj, LocalServiceObj):
            return ServiceType.LOCAL
        elif isinstance(obj, RemoteServiceObj):
            return ServiceType.REMOTE
        raise ValueError("unknown obj origin")


class ServiceObjOutputListSLZ(ServiceObjOutputSLZ):
    pass


class PlanForDisplayOutputSLZ(serializers.Serializer):
    """用于简单展示的 Plan 信息"""

    name = serializers.CharField(help_text="方案名称")
    description = serializers.CharField(help_text="方案描述")


class PlanObjOutputSLZ(serializers.Serializer):
    """增强服务计划详情"""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.CharField(source="service.uuid", read_only=True)

    uuid = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField()
    description = serializers.CharField()
    config = serializers.JSONField(required=False, default=dict)
    is_active = serializers.BooleanField()
    properties = serializers.JSONField(required=False, default=dict)


class ServiceInstanceOutputSLZ(serializers.Serializer):
    """增强服务实例"""

    uuid = serializers.UUIDField()
    config = serializers.JSONField()
    credentials = serializers.JSONField()


class ServiceCreateSLZ(serializers.Serializer):
    """创建增强服务"""

    name = serializers.CharField(help_text="名称")
    category_id = serializers.IntegerField(help_text="服务分类")
    display_name = serializers.CharField(help_text="展示用名称")
    logo = serializers.CharField()

    description = serializers.CharField(help_text="描述")
    long_description = serializers.CharField(help_text="详细描述")
    instance_tutorial = serializers.CharField(help_text="服务 markdown 描述")
    provider_name = serializers.CharField(help_text="供应商")

    config = serializers.JSONField(required=False, default=dict)

    is_visible = serializers.BooleanField(help_text="是否可见")

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        language_code = get_language()
        # 国际化相关的字段需要按当前用户的语言来确定字段
        i18n_fields = ["display_name", "description", "long_description", "instance_tutorial"]
        for _field in i18n_fields:
            # 需要将语言中的连字符转为下划线，如 zh-cn 转为: zh_cn
            _translated_field = to_translated_field(_field, language_code)
            data[_translated_field] = data.pop(_field, "")

        return data

    def validate_name(self, name: str) -> str:
        if not re.fullmatch(ADDONS_SERVICE_NAME_REGEX, name):
            raise ValidationError(
                _(
                    "{} 不符合规范: 由 3-32 位字母、数字、连接符(-)、下划线(_) 字符组成，以字母开头，字母或数字结尾"
                ).format(name)
            )  # noqa: E501

        return name


class ServiceUpdateSLZ(ServiceCreateSLZ):
    """更新增强服务"""
