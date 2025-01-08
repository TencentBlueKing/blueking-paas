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

import json

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.servicehub.remote.exceptions import ServiceConfigNotFound
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.accessories.services.models import ServiceCategory
from paasng.platform.modules.serializers import MinimalModuleSLZ


class CategorySLZ(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class ServiceMinimalSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    category = CategorySLZ()


class ServiceCategoryByRegionSLZ(serializers.Serializer):
    category = CategorySLZ()
    services = serializers.ListField(child=ServiceMinimalSLZ())


class ServiceSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    available_languages = serializers.CharField()
    display_name = serializers.CharField()
    logo = serializers.CharField()
    description = serializers.CharField()
    long_description = serializers.CharField()
    category = CategorySLZ()
    instance_tutorial = serializers.CharField()
    is_ready = serializers.SerializerMethodField()

    def get_is_ready(self, data) -> bool:
        """部分依赖其他服务的增强服务（如蓝鲸 APM），在依赖服务尚未部署前，可以通过设置 is_ready=False 来跳过创建增强服务实例的步骤。"""
        svc_store = get_remote_store()
        try:
            svc_config = svc_store.get_source_config(data.uuid)
        except ServiceConfigNotFound:
            # 本地增强服务等未显式声明 is_ready 属性的都默认为开启
            is_ready = True
        else:
            is_ready = svc_config.is_ready
        return is_ready


class ServiceSimpleFieldsSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    category = CategorySLZ()


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
    region = serializers.CharField(help_text="应用版本", allow_null=True, default="")


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

    plan_id = serializers.CharField(help_text="手动指定的方案 ID", default=None)
    env_plan_id_map = serializers.DictField(help_text="手动指定的分环境方案 ID 字典", default=None)


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


# 增强服务按名称聚合
class ServiceWithInstsSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    logo = serializers.CharField()
    category = CategorySLZ()
    display_name = serializers.CharField()
    description = serializers.CharField()
    long_description = serializers.CharField(allow_null=True, default="")
    available_languages = serializers.CharField(default="")
    instance_tutorial = serializers.CharField(default="")

    instances = serializers.ListField(allow_null=True, child=ServiceAttachmentDetailedSLZ())


class CreateSharedAttachmentsSLZ(serializers.Serializer):
    """Serializer for creating shared service attachment"""

    ref_module_name = serializers.CharField(help_text="被共享的模块名称")


class ProvisionInfoSLZ(serializers.Serializer):
    stag = serializers.BooleanField(help_text="是否已配置实例(预发布环境)", default=False)
    prod = serializers.BooleanField(help_text="是否已配置实例(生产环境)", default=False)


class PlanForDisplaySLZ(serializers.Serializer):
    """用于简单展示的 Plan 信息"""

    name = serializers.CharField(help_text="方案名称")
    description = serializers.CharField(help_text="方案描述")


class BoundPlansSLZ(serializers.Serializer):
    stag = PlanForDisplaySLZ(help_text="预发布环境方案信息", default=None)
    prod = PlanForDisplaySLZ(help_text="生产环境方案信息", default=None)


class BoundServiceInfoSLZ(serializers.Serializer):
    """Serializer for representing bound service info"""

    service = ServiceMinimalSLZ(help_text="增强服务信息")
    provision_infos = ProvisionInfoSLZ(help_text="增强服务实例分配信息")
    plans = BoundPlansSLZ(help_text="增强服务方案信息")
    ref_modules = serializers.ListField(help_text="共享当前增强服务的模块", allow_null=True, child=MinimalModuleSLZ())


class SharedServiceInfoSLZ(serializers.Serializer):
    """Serializer for representing shared service info"""

    module = MinimalModuleSLZ(help_text="发起共享的模块")
    ref_module = MinimalModuleSLZ(help_text="被共享的模块")
    service = ServiceMinimalSLZ(help_text="共享服务信息")


class SharedServiceInfoWithAllocationSLZ(SharedServiceInfoSLZ):
    """携带分配 & 配置信息的共享服务信息"""

    provision_infos = ProvisionInfoSLZ(help_text="共享服务实例分配信息")


class ServiceEngineAppAttachmentSLZ(serializers.Serializer):
    environment = serializers.CharField(source="engine_app.env.environment")
    credentials_enabled = serializers.BooleanField(help_text="是否使用凭证")


class UpdateServiceEngineAppAttachmentSLZ(serializers.Serializer):
    credentials_enabled = serializers.BooleanField(help_text="是否使用凭证")


class UnboundServiceInstanceInfoSLZ(serializers.Serializer):
    instance_id = serializers.UUIDField(help_text="增强服务实例 id")
    service_instance = ServiceInstanceSLZ(help_text="增强服务实例信息")
    environment = serializers.CharField(help_text="环境")
    environment_name = serializers.CharField(help_text="环境名称")


class UnboundServiceEngineAppAttachmentSLZ(serializers.Serializer):
    service = ServiceMinimalSLZ(help_text="增强服务信息")
    unbound_instances = UnboundServiceInstanceInfoSLZ(many=True, help_text="已解绑增强服务实例")
    count = serializers.SerializerMethodField(help_text="数量")

    def get_count(self, obj):
        return len(obj.get("unbound_instances", []))


class DeleteUnboundServiceEngineAppAttachmentSLZ(serializers.Serializer):
    instance_id = serializers.UUIDField(help_text="增强服务实例 id")


class PossiblePlansOutputSLZ(serializers.Serializer):
    """The possible plans for a service"""

    has_multiple_plans = serializers.BooleanField(help_text="是否存在多个可选方案", read_only=True)
    static_plans = serializers.ListField(
        help_text="静态方案列表", child=serializers.DictField(), default=None, read_only=True
    )
    env_specific_plans = serializers.DictField(help_text="环境特定方案列表", default=None, read_only=True)
