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
import json

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.services.models import ServiceCategory
from paasng.platform.modules.serializers import MinimalModuleSLZ


class CategorySLZ(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class SpecDefinitionSLZ(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    recommended_value = serializers.CharField(allow_null=True)


class ServiceMinimalSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    category = CategorySLZ()
    specifications = serializers.ListField(child=SpecDefinitionSLZ(), source="public_specifications")


class ServiceCategoryByRegionSLZ(serializers.Serializer):
    category = CategorySLZ()
    services = serializers.ListField(child=ServiceMinimalSLZ())


class ServiceSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    region = serializers.CharField()
    name = serializers.CharField()
    available_languages = serializers.CharField()
    display_name = serializers.CharField()
    logo = serializers.CharField()
    description = serializers.CharField()
    long_description = serializers.CharField()
    category = CategorySLZ()
    specifications = serializers.ListField(child=SpecDefinitionSLZ(), source="public_specifications")
    instance_tutorial = serializers.CharField()


class ServiceWithSpecsSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    category = CategorySLZ()
    specs = serializers.ListField(allow_null=True, default=None)


class SingleServiceSpecificationSLZ(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    recommended_value = serializers.CharField()


class ServicePlanSpecificationSLZ(SingleServiceSpecificationSLZ):
    value = serializers.CharField()


class ServiceSpecificationSLZ(serializers.Serializer):
    definitions = serializers.ListField(child=SingleServiceSpecificationSLZ(), allow_empty=True)
    recommended_values = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    values = serializers.ListField(child=serializers.ListField(child=serializers.CharField()), allow_empty=True)


class ApplicationWithLogoSLZ(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField()
    language = serializers.CharField()
    type = serializers.CharField(help_text="应用类型")
    logo_url = serializers.CharField(help_text="Logo 图片", read_only=True, source="get_logo_url")


class EnvServiceAttachmentSLZ(serializers.Serializer):
    """部署环境增强服务附件配置状态"""

    service = ServiceMinimalSLZ(source="get_service")
    is_provisioned = serializers.BooleanField(help_text="是否已配置实例")


class EnvServiceInfoSLZ(serializers.Serializer):
    """单个环境增强服务详情"""

    name = serializers.CharField()
    display_name = serializers.CharField()
    is_provisioned = serializers.BooleanField(required=False, default=False)
    service_id = serializers.CharField(required=False, default="")
    category_id = serializers.IntegerField(required=False, default=0)


class ModuleServiceInfoSLZ(serializers.Serializer):
    """单个模块增强服务详情"""

    prod = serializers.ListField(child=EnvServiceInfoSLZ())
    stag = serializers.ListField(child=EnvServiceInfoSLZ())


class ServiceAttachmentSLZ(serializers.Serializer):
    """模块增强服务附件-序列化器"""

    id = serializers.IntegerField(help_text="id for [Remote/Local]ServiceModuleAttachment")
    application = ApplicationWithLogoSLZ()
    module_name = serializers.CharField()
    service = serializers.CharField()


class ServiceAttachmentDetailedSLZ(ServiceAttachmentSLZ):
    created = serializers.DateTimeField()
    region = serializers.CharField(allow_null=True, default="")


class ServiceAttachmentQuerySLZ(serializers.Serializer):
    valid_order_by_fields = ("created",)
    order_by = serializers.CharField(default="-created")

    def validate(self, data):
        value = data["order_by"]
        if value.startswith("-"):
            value = "-%s" % value.lstrip("-")

        if value.lstrip("-") not in self.valid_order_by_fields:
            raise ValidationError("无效的排序选项：%s" % value)

        return data


class CreateAttachmentSLZ(serializers.Serializer):
    service_id = serializers.CharField()
    module_name = serializers.CharField(required=False)
    code = serializers.CharField()
    specs = serializers.DictField(default=dict)


class ServiceInstanceSLZ(serializers.Serializer):
    """增强服务实例-序列化器"""

    config = serializers.JSONField()
    credentials = serializers.JSONField(source="credentials_insensitive")

    def to_representation(self, instance):
        data = super(ServiceInstanceSLZ, self).to_representation(instance)
        data["sensitive_fields"] = instance.should_remove_fields
        data["hidden_fields"] = instance.get_hidden_credentials()

        # The client side needs string version instead of object type for credentials, which is
        # really confusing.
        data["credentials"] = json.dumps(data["credentials"])
        return data


class ServiceInstanceInfoSLZ(serializers.Serializer):
    service_instance = ServiceInstanceSLZ()
    environment = serializers.CharField()
    environment_name = serializers.CharField()
    usage = serializers.CharField()
    service_specs = serializers.DictField(child=serializers.CharField())


# 增强服务按名称聚合
class ServiceSetGroupByNameSLZ(serializers.Serializer):
    name = serializers.CharField()
    logo = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    long_description = serializers.CharField(allow_null=True, default="")
    available_languages = serializers.CharField(default="")
    instance_tutorial = serializers.CharField(default="")

    enabled_regions = serializers.ListField(child=serializers.CharField())
    services = serializers.ListField(child=ServiceMinimalSLZ())
    instances = serializers.ListField(allow_null=True, child=ServiceAttachmentDetailedSLZ())


class CreateSharedAttachmentsSLZ(serializers.Serializer):
    """Serializer for creating shared service attachment"""

    ref_module_name = serializers.CharField(help_text="被共享的模块名称")


class ProvisionInfoSLZ(serializers.Serializer):
    stag = serializers.BooleanField(help_text="是否已配置实例(预发布环境)", default=False)
    prod = serializers.BooleanField(help_text="是否已配置实例(生产环境)", default=False)


class BoundServiceInfoSLZ(serializers.Serializer):
    """Serializer for representing bound service info"""

    service = ServiceMinimalSLZ(help_text="增强服务信息")
    provision_infos = ProvisionInfoSLZ(help_text="增强服务实例分配信息")
    specifications = serializers.ListField(help_text="配置信息", allow_null=True, child=ServicePlanSpecificationSLZ())
    ref_modules = serializers.ListField(help_text="共享当前增强服务的模块", allow_null=True, child=MinimalModuleSLZ())


class SharedServiceInfoSLZ(serializers.Serializer):
    """Serializer for representing shared service info"""

    module = MinimalModuleSLZ(help_text="发起共享的模块")
    ref_module = MinimalModuleSLZ(help_text="被共享的模块")
    service = ServiceMinimalSLZ(help_text="共享服务信息")


class SharedServiceInfoWithAllocationSLZ(SharedServiceInfoSLZ):
    """携带分配 & 配置信息的共享服务信息"""

    provision_infos = ProvisionInfoSLZ(help_text="共享服务实例分配信息")
    specifications = serializers.ListField(help_text="配置信息", allow_null=True, child=ServicePlanSpecificationSLZ())


class ServiceEngineAppAttachmentSLZ(serializers.Serializer):
    environment = serializers.CharField(source="engine_app.env.environment")
    credentials_enabled = serializers.BooleanField(help_text="是否使用凭证")


class UpdateServiceEngineAppAttachmentSLZ(serializers.Serializer):
    credentials_enabled = serializers.BooleanField(help_text="是否使用凭证")
