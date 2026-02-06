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

from .models import Sandbox


class SandboxCreateInputSLZ(serializers.Serializer):
    """The serializer for creating sandbox."""

    name = serializers.CharField(label="名称", max_length=64, required=False, help_text="不提供则基于 UUID 生成")
    env = serializers.JSONField(label="环境变量", required=False, default=dict, help_text="用于注入到沙箱内的环境变量")


class SandboxCreateOutputSLZ(serializers.ModelSerializer):
    """The serializer for creating sandbox output."""

    class Meta:
        model = Sandbox
        fields = (
            "uuid",
            "name",
            "snapshot",
            "target",
            "env",
            "cpu",
            "memory",
            "status",
            "created",
        )
