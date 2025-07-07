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


class ProcessComponentCreateInputSLZ(serializers.Serializer):
    type = serializers.CharField(max_length=32)
    version = serializers.CharField(max_length=32)
    enabled = serializers.BooleanField()
    description = serializers.CharField(allow_null=True, required=False)
    docs_url = serializers.CharField(max_length=255, allow_null=True, required=False)
    properties_json_schema = serializers.JSONField(required=False, default=dict)


class ProcessComponentOutputSLZ(serializers.Serializer):
    uuid = serializers.UUIDField(help_text="UUID of process component")
    type = serializers.CharField()
    version = serializers.CharField()
    enabled = serializers.BooleanField()
    description = serializers.CharField(allow_null=True, required=False)
    docs_url = serializers.CharField(allow_null=True, required=False)
    properties_json_schema = serializers.JSONField(required=False, default=dict)


class ProcessComponentUpdateInputSLZ(serializers.Serializer):
    enabled = serializers.BooleanField()
    description = serializers.CharField(allow_null=True, required=False)
    docs_url = serializers.CharField(max_length=255, allow_null=True, required=False)
    properties_json_schema = serializers.JSONField(required=False, default=dict)
