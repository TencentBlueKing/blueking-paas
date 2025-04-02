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
import logging
from typing import Dict, List

from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings
from typing_extensions import Protocol

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.infras.bk_cmsi.backend.apigw import Client
from paasng.infras.bk_cmsi.backend.apigw import Group as BkCmsiGroup
from paasng.infras.bk_cmsi.backend.esb import get_client_by_username

logger = logging.getLogger(__name__)


class BkCmsiBackend(Protocol):
    """Describes protocols of calling API service"""

    def call_api(self, *args, **kwargs) -> bool: ...


class BkCmsiApiGwClient:
    """由 API 网关提供的消息通知 API"""

    def __init__(self, tenant_id: str, stage: str = "prod"):
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers({API_HERDER_TENANT_ID: tenant_id})
        self.client: BkCmsiGroup = client.api

    def call_api(self, method: str, params: Dict) -> bool:
        # 如果 API 网关上未注册该通知渠道，则跳过发送，不需要阻塞后续流程所以返回 True
        if not hasattr(self.client, method):
            logger.warning(
                "%s is not registered on API Gateway, skip sending notifications, params: %s", method, params
            )
            return True

        try:
            result = getattr(self.client, method)(json=params)
        except (APIGatewayResponseError, ResponseError):
            logging.exception("call bk_cmsi api error, method: %s, params: %s", method, params)
            return False

        logger.debug("call bk_cmsi api success, result:%s", result)
        return True


class BkCmsiEsbClient:
    """由 ESB 提供的消息通知 API"""

    def __init__(self):
        # ESB 开启了免用户认证，但限制用户名不能为空，因此给默认用户名
        # 调用 ESB 需要使用特殊的应用 ID ，不是默认的 settings.BK_APP_CODE
        esb_client = get_client_by_username(
            "admin", bk_app_code=settings.BKAUTH_TOKEN_APP_CODE, bk_app_secret=settings.BKAUTH_TOKEN_SECRET_KEY
        )
        self.client = esb_client.api

    def call_api(self, method: str, params: Dict) -> bool:
        # 如果 ESB 上未注册该通知渠道，则跳过发送，不需要阻塞后续流程所以返回 True
        if not hasattr(self.client, method):
            logger.warning("%s is not registered on ESB, skip sending notifications, params: %s", method, params)
            return True

        try:
            result = getattr(self.client, method)(json=params)
        except Exception:
            logging.exception("call bk_cmsi api error, method: %s, params: %s", method, params)
            return False

        # ESB 不管调用成员与否，状态码都会返回 200，需要通过 result 字段判断是否成功
        if result.get("result"):
            return True

        logger.error("call bk_cmsi api failed: %s, method: %s, params: %s", result, method, params)
        return False


def make_bk_cmsi_client(tenant_id: str, stage: str = "prod") -> BkCmsiBackend:
    """创建消息通知服务客户端工厂函数

    :param tenant_id: 租户ID。多租户模式下，消息的接收人必须在该租户下
    :param stage: 网关环境，默认为正式环境
    """
    # 多租户模式下使用 API网关 API
    if settings.ENABLE_MULTI_TENANT_MODE:
        return BkCmsiApiGwClient(tenant_id, stage)
    else:
        # 非多租户模式下使用 ESB API
        return BkCmsiEsbClient()


class BkNotificationService:
    """蓝鲸消息通知服务，包含以下通知渠道：
    - 邮件通知
    - 企业微信通知（仅在特定版本支持，不支持的版本调用时会跳过调用并返回 True)
    - 微信通知
    - 短信通知
    """

    def __init__(self, tenant_id: str, stage: str = "prod"):
        self.client = make_bk_cmsi_client(tenant_id, stage)

    def send_mail(self, receivers: List[str], content: str, title: str) -> bool:
        """发送邮件通知

        :param receivers: 接收人列表
        :param content: 邮件内容
        :param title: 邮件主题
        """
        if not receivers:
            logger.error("The receivers of sending mail is empty, skipped")
            return False

        params = {
            "content": content,
            "title": title,
            "receiver__username": receivers,
        }
        return self.client.call_api("send_mail", params)

    def send_weixin(self, receivers: List[str], content: str, title: str) -> bool:
        """发送微信通知

        :param receivers: 接收人列表
        :param content: 通知文字
        :param title: 通知头部文字
        """
        if not receivers:
            logger.error("The receivers of sending weixin is empty, skipped")
            return False

        params = {
            "data": {"heading": title, "message": content},
            "receiver__username": receivers,
        }
        return self.client.call_api("send_weixin", params)

    def send_wecom(self, receivers: List[str], content: str, title: str) -> bool:
        """发送 WeCom(企业微信) 通知，仅特定版本的 ESB API 支持

        :param receivers: 接收人列表
        :param content: 通知内容正文
        :param title: 通知标题
        """
        if not receivers:
            logger.error("The receivers of sending rtx is empty, skipped")
            return False

        params = {
            "content": content,
            "title": title,
            "receiver__username": receivers,
        }
        return self.client.call_api("send_rtx", params)

    def send_sms(self, receivers: List[str], content: str) -> bool:
        """发送短信通知

        :param receivers: 接收人列表
        :param content: 通知内容正文，如果是使用腾讯云等通道需要提前配置好通知模板
        """
        if not receivers:
            logger.error("The receivers of sending SMS is empty, skipped")
            return False

        params = {
            "receiver__username": receivers,
            "content": content,
        }
        return self.client.call_api("send_sms", params)
