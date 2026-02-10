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
import base64
import binascii
import json
from typing import Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.accessories.services.constants import PreCreatedInstanceAllocationType
from paasng.plat_mgt.infras.services.constants import TLS_STRING_FIELDS


class PreCreatedInstanceBindingPolicySLZ(serializers.Serializer):
    app_code = serializers.CharField(help_text="应用编码", required=False)
    module_name = serializers.CharField(help_text="模块名称", required=False)
    env_name = serializers.CharField(help_text="环境名称", required=False)


class PreCreatedInstanceBindingPolicyInputSLZ(PreCreatedInstanceBindingPolicySLZ):
    def validate(self, attrs):
        if all(attrs.get(field, "") == "" for field in ("app_code", "module_name", "env_name")):
            raise serializers.ValidationError(_("至少需要指定一个匹配规则, 且匹配规则不能为空字符串"))
        return super().validate(attrs)


class PreCreatedInstanceBindingPolicyOutputSLZ(PreCreatedInstanceBindingPolicySLZ):
    pass


class PreCreatedInstanceUpsertSLZ(serializers.Serializer):
    config = serializers.JSONField(help_text="预创建实例的配置")
    credentials = serializers.JSONField(help_text="预创建实例的凭据")
    binding_policy = PreCreatedInstanceBindingPolicyInputSLZ(help_text="实例绑定策略", required=False, default=dict)
    allocation_type = serializers.ChoiceField(
        help_text="预创建实例的分配类型",
        choices=PreCreatedInstanceAllocationType.get_django_choices(),
    )

    # 对 config.tls base64 编码后入库, 后续可以直接用于创建 k8s Secret
    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # tls 和前端约定放在 config.tls 下
        tls_info = data.get("config", {}).get("tls")
        if not tls_info or not isinstance(tls_info, dict):
            return data

        tls_info = tls_info.copy()
        for k in TLS_STRING_FIELDS:
            val = tls_info.get(k)
            if val:
                tls_info[k] = base64.b64encode(val.encode()).decode()
        data["config"]["tls"] = tls_info
        return data

    def validate(self, attrs):
        allocation_type = attrs["allocation_type"]
        has_policy = bool(attrs.get("binding_policy"))

        if allocation_type == PreCreatedInstanceAllocationType.POLICY and not has_policy:
            raise ValidationError(_("POLICY 类型的预创建实例必须指定 binding_policy"))
        if allocation_type == PreCreatedInstanceAllocationType.FIFO and has_policy:
            raise ValidationError(_("FIFO 类型的预创建实例不允许指定 binding_policy"))
        return attrs


class PreCreatedInstanceOutputSLZ(serializers.Serializer):
    plan_id = serializers.CharField(help_text="方案 ID", source="plan.uuid")
    uuid = serializers.CharField(help_text="实例 ID")
    config = serializers.JSONField(help_text="预创建实例的配置")
    credentials = serializers.JSONField(help_text="预创建实例的凭据")
    is_allocated = serializers.BooleanField(help_text="实例是否已被分配")
    tenant_id = serializers.CharField(help_text="租户 id")
    binding_policy = serializers.SerializerMethodField(help_text="实例绑定策略")

    def get_binding_policy(self, instance) -> Dict:
        policy = instance.binding_policies.first()
        if not policy:
            return {}
        return PreCreatedInstanceBindingPolicyOutputSLZ(policy).data

    def to_representation(self, instance) -> Dict:
        result = super().to_representation(instance)
        # config 以 dict 形式返回
        if isinstance(result["config"], str):
            result["config"] = json.loads(result["config"])

        tls_info = result["config"].get("tls")
        if not (tls_info and isinstance(tls_info, dict)):
            return result

        for k in TLS_STRING_FIELDS:
            if val := tls_info.get(k):
                try:
                    tls_info[k] = base64.b64decode(val.encode()).decode()
                except (binascii.Error, UnicodeDecodeError):
                    tls_info[k] = val
        return result
