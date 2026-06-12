# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from blue_krill.data_types.enum import EnumField, IntStructuredEnum

from paasng.utils.basic import ChoicesEnum


class PluginTagIdType(IntStructuredEnum):
    UNTAGGED = EnumField(-1, label="未分类")


# AI Agent 插件应用的模板 ID 以 bk-ai 开头
AI_AGENT_TEMPLATE_PREFIX = "bk-ai"


class EventType(ChoicesEnum):
    """这些事件类型用来区分由部署等行为产生的流式信息。"""

    INIT = "init"
    CLOSE = "close"
    MSG = "msg"
    TITLE = "title"

    _choices_labels = [(INIT, "初始化"), (CLOSE, "关闭通道"), (MSG, "消息"), (TITLE, "标题")]
