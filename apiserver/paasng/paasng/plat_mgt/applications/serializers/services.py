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

from paasng.plat_mgt.infras.services.serializers import (
    PlanForDisplayOutputSLZ,
)
from paasng.platform.modules.serializers import MinimalModuleSLZ


class ServiceMinimalObjSLZ(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()


class ServicePlanOutputSLZ(serializers.Serializer):
    """应用增强服务绑定计划序列化器"""

    stag = PlanForDisplayOutputSLZ(help_text="预发布环境方案信息", default=None)
    prod = PlanForDisplayOutputSLZ(help_text="生产环境方案信息", default=None)


class ServiceProvisionInfoSLZ(serializers.Serializer):
    env_name = serializers.CharField(help_text="环境名称")
    is_provisioned = serializers.BooleanField(help_text="是否已分配实例")
    instance_uuid = serializers.UUIDField(help_text="增强服务实例唯一标识", allow_null=True, default=None)


class BoundServiceInfoOutPutSLZ(serializers.Serializer):
    """应用增强服务绑定信息序列化器"""

    service = ServiceMinimalObjSLZ(help_text="增强服务信息")
    provision_infos = ServiceProvisionInfoSLZ(help_text="增强服务实例分配信息", many=True)
    plans = ServicePlanOutputSLZ(help_text="增强服务方案信息")
    ref_modules = serializers.ListField(help_text="共享当前增强服务的模块", allow_null=True, child=MinimalModuleSLZ())


class SharedServiceInfoOutputSLZ(serializers.Serializer):
    """应用增强服务共享信息序列化器"""

    module = MinimalModuleSLZ(help_text="发起共享的模块")
    ref_module = MinimalModuleSLZ(help_text="被共享的模块")
    service = ServiceMinimalObjSLZ(help_text="共享服务信息")
    provision_infos = ServiceProvisionInfoSLZ(help_text="共享服务实例分配信息", many=True)


class ServiceListOutputSLZ(serializers.Serializer):
    """应用模块增强服务列表"""

    module_name = serializers.CharField(help_text="模块名称")
    bound_services = BoundServiceInfoOutPutSLZ(many=True, help_text="绑定的增强服务列表")
    shared_services = SharedServiceInfoOutputSLZ(many=True, help_text="共享的增强服务列表")
