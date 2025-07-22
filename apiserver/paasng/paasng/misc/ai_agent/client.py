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
import logging

import requests
from django.conf import settings
from requests.auth import AuthBase

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.misc.ai_agent.exceptions import AIAgentServiceError
from paasng.utils import masked_curlify

logger = logging.getLogger(__name__)


class APIGatewayHeaderAuth(AuthBase):
    def __init__(self, credential: str, tenant_id: str):
        self.credential = credential
        self.tenant_id = tenant_id

    def __call__(self, r):
        r.headers["X-Bkapi-Authorization"] = json.dumps(
            {
                "bk_app_code": settings.BK_APP_CODE,
                "bk_app_secret": settings.BK_APP_SECRET,
                settings.BK_COOKIE_NAME: self.credential,
            }
        )
        r.headers[API_HERDER_TENANT_ID] = self.tenant_id
        r.headers["Content-Type"] = "application/json"
        # 禁用客户端和代理缓存，确保每次请求都获取最新响应
        # no-cache: 不直接使用缓存，必须向服务器验证资源有效性
        r.headers["Cache-Control"] = "no-cache"
        # 禁用 Nginx 代理缓冲，用于实时流式传输场景
        # no: 关闭代理缓冲，允许服务器直接推送数据到客户端
        r.headers["X-Accel-Buffering"] = "no"
        return r


class AIAgentClient:
    """开发中心 AI 智能体（ai-bkpaas）插件通过 APIGW 提供的 API

    NOTE: API 为流式调用，所以不能使用 APIGW 提供的 SDK
    """

    AI_AGENT_GATEWAY_NAME = "bp-ai-bkpaas"

    def __init__(self, tenant_id: str, credential: str, stage: str = "prod"):
        """
        :param tenant_id: 租户 ID
        :param credential: 用户凭证（bk_ticket / bk_token）
        :param stage: 网关环境
        """
        self.client = requests.Session()
        self.client.auth = APIGatewayHeaderAuth(credential, tenant_id)
        self.url_prefix = f"{settings.BK_API_URL_TMPL.format(api_name=self.AI_AGENT_GATEWAY_NAME)}/{stage}"

    def chat_completion(self, input: str, operator: str, chat_history: list):
        """流式调用 AI 助手的聊天接口

        :param input: 用户输入
        :param operator: 操作者
        :param chat_history: 聊天历史
        :return: 流式响应对象
        """
        url = f"{self.url_prefix}/bk_plugin/plugin_api/chat_completion/"

        # bkaidev 要求 必须要有一对对话，因此这里加一条历史记录
        new_chat_history = [
            {"role": "user", "content": "hi"},
        ]
        new_chat_history.extend(chat_history)
        data = {
            "inputs": {
                "input": input,
                "chat_history": new_chat_history,
            },
            "context": {"executor": operator},
        }

        try:
            response = self.client.post(url, json=data, stream=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # 记录详细错误信息
            error_msg = f"call chat completion error: {str(e)}"
            logging.exception(
                f"{error_msg}\n"
                f"URL: {url}\n"
                f"Request: {masked_curlify.to_curl(response.request)}\n"
                f"Response: {response.text}"
            )
            raise AIAgentServiceError(error_msg) from e
        return response
