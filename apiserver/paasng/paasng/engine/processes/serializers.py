# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from rest_framework import serializers


class ProcessSpecSLZ(serializers.Serializer):
    """Serializer for displaying process specifications"""

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField(source='plan.max_replicas')
    resource_limit = serializers.JSONField(source='plan.limits')


class WebConsoleOpenSLZ(serializers.Serializer):
    container_name = serializers.CharField(required=False, default=None, allow_null=True, help_text="容器名称")


class WebConsoleResultSLZ(serializers.Serializer):
    web_console_url = serializers.CharField(help_text="控制台入口地址")
    session_id = serializers.CharField(help_text="会话 ID")
    code = serializers.IntegerField(help_text="状态码")
    message = serializers.CharField(help_text="消息")
    request_id = serializers.CharField(help_text="请求 ID")


class ProcessFilterQuerySLZ(serializers.Serializer):
    release_id = serializers.CharField(default=None, help_text="需要过滤的发布实例id")
