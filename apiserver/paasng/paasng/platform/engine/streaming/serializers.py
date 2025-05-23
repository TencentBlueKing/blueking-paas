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

from .constants import EventType


class HistoryEventsQuerySLZ(serializers.Serializer):
    last_event_id = serializers.IntegerField(default=0, required=False, help_text="最后一个事件id")


class StreamEventSLZ(serializers.Serializer):
    """流式事件序列化器"""

    id = serializers.IntegerField(help_text="事件id")
    event = serializers.ChoiceField(
        EventType.get_choices(),
        help_text="事件类型",
    )
    data = serializers.CharField(help_text="事件内容")


class StreamingQuerySLZ(serializers.Serializer):
    """用于流式传输接口的查询参数序列化器"""

    include_ansi_codes = serializers.BooleanField(
        default=False,
        required=False,
        help_text="是否包含 ANSI 转义序列",
    )
