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
from django.utils.translation import get_language
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.dev_resources.servicehub.local.manager import LocalServiceObj
from paasng.dev_resources.servicehub.remote.manager import RemoteServiceObj
from paasng.dev_resources.servicehub.services import ServiceSpecificationDefinition
from paasng.dev_resources.services.models import Plan, PreCreatedInstance
from paasng.plat_admin.admin42.serializers.engine import EnvironmentSLZ
from paasng.utils.i18n import to_translated_field


class ServiceSpecificationDefinitionSLZ(serializers.Serializer):
    def to_representation(self, instance: ServiceSpecificationDefinition):
        data = instance.as_dict()
        # 去除辅助字段
        data.pop("is_public")
        return data

    def to_internal_value(self, data):
        try:
            ServiceSpecificationDefinition(**data)
        except ValueError:
            raise ValidationError
        # 去除辅助字段
        data.pop("is_public", None)
        return data


class ServiceObjSLZ(serializers.Serializer):
    uuid = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    region = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    name = serializers.CharField()
    category_id = serializers.IntegerField()
    display_name = serializers.CharField()
    logo = serializers.CharField()

    description = serializers.CharField()
    long_description = serializers.CharField()
    instance_tutorial = serializers.CharField()

    available_languages = serializers.CharField()
    config = serializers.JSONField(required=False, default=dict)

    is_active = serializers.BooleanField()
    is_visible = serializers.BooleanField()
    specifications = ServiceSpecificationDefinitionSLZ(many=True)

    provider_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    origin = serializers.SerializerMethodField()

    def get_origin(self, obj):
        if isinstance(obj, LocalServiceObj):
            return "local"
        elif isinstance(obj, RemoteServiceObj):
            return "remote"
        raise ValueError("unknown obj origin")

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        language_code = get_language()
        # 国际化相关的字段需要按当前用户的语言来确定字段
        i18n_fields = ['display_name', 'description', 'long_description', 'instance_tutorial']
        for _field in i18n_fields:
            # 需要将语言中的连字符转为下划线，如 zh-cn 转为: zh_cn
            _translated_field = to_translated_field(_field, language_code)
            data[_translated_field] = data.pop(_field, "")

        return data


class PlanObjSLZ(serializers.Serializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.CharField(source="service.uuid", read_only=True)

    uuid = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    region = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField()
    description = serializers.CharField()
    config = serializers.JSONField(required=False, default=dict)
    is_active = serializers.BooleanField()
    specifications = serializers.JSONField()
    properties = serializers.JSONField(required=False, default=dict)


class PlanSLZ(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    region = serializers.CharField(source="service.region", read_only=True)

    class Meta:
        model = Plan
        fields = '__all__'


class PreCreatedInstanceSLZ(serializers.ModelSerializer):
    config = serializers.JSONField()

    class Meta:
        model = PreCreatedInstance
        fields = '__all__'


class PlanWithPreCreatedInstanceSLZ(PlanSLZ):
    pre_created_instances = PreCreatedInstanceSLZ(many=True, read_only=True, source="precreatedinstance_set")


class ServiceInstanceSLZ(serializers.Serializer):
    uuid = serializers.UUIDField()
    config = serializers.JSONField()
    credentials = serializers.JSONField()


class ServiceInstanceBindInfoSLZ(serializers.Serializer):
    instance = ServiceInstanceSLZ()
    environment = EnvironmentSLZ()
    module = serializers.CharField(help_text="模块名称")
    plan = PlanObjSLZ()
    service = ServiceObjSLZ()
