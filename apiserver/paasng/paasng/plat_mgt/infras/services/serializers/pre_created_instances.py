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
from typing import Dict

from rest_framework import serializers


class PreCreatedInstanceUpsertSLZ(serializers.Serializer):
    config = serializers.JSONField(help_text="预创建实例的配置")
    credentials = serializers.JSONField(help_text="预创建实例的凭据")


class PreCreatedInstanceOutputSLZ(serializers.Serializer):
    plan_id = serializers.CharField(help_text="方案 ID", source="plan.uuid")
    uuid = serializers.CharField(help_text="实例 ID")
    config = serializers.JSONField(help_text="预创建实例的配置")
    credentials = serializers.JSONField(help_text="预创建实例的凭据")
    is_allocated = serializers.BooleanField(help_text="实例是否已被分配")
    tenant_id = serializers.CharField(help_text="租户 id")

    def to_representation(self, instance) -> Dict:
        result = super().to_representation(instance)
        # config 以 dict 形式返回
        if isinstance(result["config"], str):
            result["config"] = json.loads(result["config"])

        return result
