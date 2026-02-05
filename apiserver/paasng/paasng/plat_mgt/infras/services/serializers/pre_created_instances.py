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
import json
from typing import Dict

from rest_framework import serializers


class PreCreatedInstanceBindingPolicyInputSLZ(serializers.Serializer):
    app_code = serializers.CharField(help_text="应用编码", required=False)
    module_name = serializers.CharField(help_text="模块名称", required=False)
    env = serializers.CharField(help_text="环境名称", required=False)

    def to_internal_value(self, data):
        # 去除空格 和 去除空字符串的键值对
        result = {}
        for key, _val in data.items():
            val = str(_val).strip()
            if val == "":
                continue
            result[key] = val
        return super().to_internal_value(result)


class PreCreatedInstanceUpsertSLZ(serializers.Serializer):
    config = serializers.JSONField(help_text="预创建实例的配置")
    credentials = serializers.JSONField(help_text="预创建实例的凭据")
    binding_policy = PreCreatedInstanceBindingPolicyInputSLZ(help_text="实例绑定策略", required=False, default=dict)

    # 对 config.tls base64 编码
    def validate_config(self, value):
        tls_info = value.get("tls")
        if not isinstance(tls_info, dict):
            return value

        data = value.copy()
        tls_info = tls_info.copy()
        for k in ("cert", "key", "ca"):
            val = tls_info.get(k)
            if val:
                tls_info[k] = base64.b64encode(val.encode()).decode()
        data["tls"] = tls_info
        return data


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
        return PreCreatedInstanceBindingPolicyInputSLZ(policy).data

    def to_representation(self, instance) -> Dict:
        result = super().to_representation(instance)
        # config 以 dict 形式返回
        if isinstance(result["config"], str):
            result["config"] = json.loads(result["config"])

        tls_info = result["config"].get("tls")
        if not (tls_info and isinstance(tls_info, dict)):
            return result

        for k in ("cert", "key", "ca"):
            if val := tls_info.get(k):
                tls_info[k] = base64.b64decode(val.encode()).decode()
        return result
