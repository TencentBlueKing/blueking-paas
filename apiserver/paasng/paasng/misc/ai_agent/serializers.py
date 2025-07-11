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


class AssistantInputSerializer(serializers.Serializer):
    """AI 助手输入参数序列化器"""

    chat_history = serializers.ListField(child=serializers.DictField(), required=True, help_text="聊天历史记录")
    input = serializers.CharField(required=True, help_text="用户输入")


class AssistantRequestSerializer(serializers.Serializer):
    """AI 助手请求体序列化器"""

    inputs = AssistantInputSerializer(required=True)
