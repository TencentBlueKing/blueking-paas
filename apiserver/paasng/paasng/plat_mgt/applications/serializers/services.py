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

from paasng.plat_admin.admin42.serializers.services import PlanObjSLZ, ServiceInstanceSLZ, ServiceObjSLZ
from paasng.platform.engine.constants import AppEnvName


class ApplicationAddonServicesObjSLZ(ServiceObjSLZ):
    """应用增强服务对象序列化器"""

    # 继承自 admin42 的序列化器


class ApplicationAddonServicesInstanceSLZ(ServiceInstanceSLZ):
    """应用增强服务实例序列化器"""


class ApplicationAddonServicesPlanSLZ(PlanObjSLZ):
    """应用增强服务计划序列化器"""

    # 继承自 admin42 的序列化器


class ApplicationAddonServicesConfigSLZ(serializers.Serializer):
    """应用增强服务环境序列化器"""

    env_name = serializers.ChoiceField(choices=AppEnvName.get_choices(), help_text="环境名称")
    is_deploy_instance = serializers.BooleanField(help_text="是否分配实例")
    plan_name = serializers.CharField(help_text="增强服务计划名称")
    plan_description = serializers.CharField(help_text="增强服务计划描述")


class ApplicationAddonServicesSLZ(serializers.Serializer):
    """应用增强服务对象序列化器"""

    service_uuid = serializers.CharField(help_text="增强服务 ID")
    service_name = serializers.CharField(help_text="增强服务名称")
    is_shared = serializers.BooleanField(default=False, help_text="是否共享服务")
    shared_from = serializers.CharField(allow_null=True, required=False, help_text="共享自哪个模块")
    config = serializers.ListField(child=ApplicationAddonServicesConfigSLZ(), help_text="增强服务环境")


class ApplicationAddonServicesListOutputSLZ(serializers.Serializer):
    """应用模块增强服务列表"""

    module_name = serializers.CharField(help_text="模块名称")
    addons_service = serializers.ListField(
        child=ApplicationAddonServicesSLZ(), help_text="增强服务列表", required=False, default=list
    )
