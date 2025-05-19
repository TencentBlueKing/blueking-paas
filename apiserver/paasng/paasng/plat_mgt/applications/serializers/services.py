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

# from paasng.accessories.servicehub.serializers import (
#     ServiceMinimalSLZ,
# )
from paasng.platform.modules.serializers import MinimalModuleSLZ


class AddonServiceSLZ(serializers.Serializer):
    """应用增强服务序列化器"""

    uuid = serializers.CharField(help_text="增强服务唯一标识")
    name = serializers.CharField(help_text="增强服务名称")
    display_name = serializers.CharField(help_text="增强服务展示名称")


class AddonServiceInstanceSLZ(serializers.Serializer):
    """应用增强服务实例序列化器"""

    uuid = serializers.UUIDField()
    config = serializers.JSONField()
    credentials = serializers.JSONField()


class AddonServicePlanSLZ(serializers.Serializer):
    """应用增强服务绑定计划序列化器"""

    env_name = serializers.CharField(help_text="环境名称")
    plan_name = serializers.CharField(help_text="增强服务计划名称")
    plan_description = serializers.CharField(help_text="增强服务计划描述")


class AddonServiceProvisionInfoSLZ(serializers.Serializer):
    stag = serializers.BooleanField(help_text="是否已配置实例(预发布环境)", default=False)
    prod = serializers.BooleanField(help_text="是否已配置实例(生产环境)", default=False)


class AddonBoundServiceInfoSLZ(serializers.Serializer):
    """Serializer for representing bound service info"""

    service = AddonServiceSLZ(help_text="增强服务信息")
    provision_infos = AddonServiceProvisionInfoSLZ(help_text="增强服务实例分配信息")
    plans = AddonServicePlanSLZ(help_text="增强服务方案信息", many=True)
    ref_modules = serializers.ListField(help_text="共享当前增强服务的模块", allow_null=True, child=MinimalModuleSLZ())


class AddonSharedServiceInfo(serializers.Serializer):
    """应用增强服务共享信息序列化器"""

    module = MinimalModuleSLZ(help_text="发起共享的模块")
    ref_module = MinimalModuleSLZ(help_text="被共享的模块")
    service = AddonServiceSLZ(help_text="共享服务信息")
    provision_infos = AddonServiceProvisionInfoSLZ(help_text="共享服务实例分配信息")


class AddonServiceListOutputSLZ(serializers.Serializer):
    """应用模块增强服务列表"""

    module_name = serializers.CharField(help_text="模块名称")
    bound_services = AddonBoundServiceInfoSLZ(many=True, help_text="绑定的增强服务列表")
    shared_services = AddonSharedServiceInfo(many=True, help_text="共享的增强服务列表")
