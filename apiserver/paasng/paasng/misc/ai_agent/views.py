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

import logging
from contextlib import closing

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.viewsets import ViewSet

from paas_wl.utils.error_codes import error_codes
from paasng.misc.ai_agent.client import AIAgentClient
from paasng.misc.ai_agent.exceptions import AIAgentServiceError
from paasng.misc.ai_agent.serializers import AssistantRequestSerializer

logger = logging.getLogger(__name__)


class AssistantView(ViewSet):
    def chat(self, request):
        """处理 AI 助手请求"""
        slz = AssistantRequestSerializer(data=request.data)
        slz.is_valid(raise_exception=True)

        inputs = slz.validated_data["inputs"]
        credential = request.COOKIES.get(settings.BK_COOKIE_NAME, "")
        username = request.user.username
        tenant_id = request.user.tenant_id

        try:
            client = AIAgentClient(tenant_id=tenant_id, credential=credential)

            stream_response = client.chat_completion(
                input=inputs["input"], operator=username, chat_history=inputs["chat_history"]
            )

            # 创建流式响应（使用内联生成器函数和自动资源管理）
            def generate_stream():
                with closing(stream_response):
                    for line in stream_response.iter_lines():
                        if line:
                            # 确保每行以换行符结束
                            yield line + b"\n"

            return StreamingHttpResponse(
                generate_stream(),
                content_type="text/event-stream; charset=utf-8",
                # no-cache: 不直接使用缓存，必须向服务器验证资源有效性
                # no: 关闭代理缓冲，允许服务器直接推送数据到客户端
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        except AIAgentServiceError:
            logger.exception("failed to call ai agent service")
            raise error_codes.AI_AGENT_SERVICE_ERROR
