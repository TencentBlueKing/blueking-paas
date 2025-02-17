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

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.services import PlanObj
from paasng.accessories.services.models import PreCreatedInstance
from paasng.utils.structure import NOTSET


class BaseServiceObjSLZ(serializers.Serializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.CharField(source="service.uuid", read_only=True)
    service_config = serializers.JSONField(source="service.config", default={}, read_only=True)


class BasePlanObjSLZ(serializers.Serializer):
    uuid = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField()
    tenant_id = serializers.CharField(help_text="所属租户")
    description = serializers.CharField()
    config = serializers.JSONField(required=False, default=dict)
    is_active = serializers.BooleanField()
    properties = serializers.JSONField(required=False, default=dict)


class PlanCreateInputSLZ(BasePlanObjSLZ):
    pass


class PreCreatedInstanceSLZ(serializers.ModelSerializer):
    config = serializers.JSONField()

    class Meta:
        model = PreCreatedInstance
        fields = "__all__"


class PlanOutputSLZ(BaseServiceObjSLZ, BasePlanObjSLZ):
    pre_created_instances = serializers.SerializerMethodField()

    def get_pre_created_instances(self, plan: PlanObj) -> list:
        # 若非资源池类型的服务, 不返回预创建实例
        if plan.service and plan.service.config.get("provider_name") != "pool":
            return []
        pre_created_instances = PreCreatedInstance.objects.filter(plan__uuid=plan.uuid)
        return PreCreatedInstanceSLZ(pre_created_instances, many=True).data


class PlanUpdateInputSLZ(BaseServiceObjSLZ, BasePlanObjSLZ):
    def validate(self, attrs):
        tenant_id = attrs["tenant_id"]
        service_id = attrs["service_id"]
        plan_id = attrs["uuid"]
        service = mixed_service_mgr.get(uuid=service_id)
        plans = service.get_plans(is_active=NOTSET)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        if not plan:
            raise serializers.ValidationError("方案不存在")

        if tenant_id != plan.tenant_id:
            raise serializers.ValidationError("不允许修改方案的租户 ID")

        return attrs
