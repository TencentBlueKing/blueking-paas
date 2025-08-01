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
from paasng.infras.notifier.backends.apigw import Client
from paasng.infras.notifier.backends.apigw import Group as BkCmsiGroup
from paasng.infras.notifier.backends.esb import get_client_by_username
from paasng.infras.notifier.exceptions import (
    InvalidNotificationParams,
    MethodNotDefinedError,
    NotificationSendFailedError,
)

logger = logging.getLogger(__name__)


class BkCmsiBackend(Protocol):
    """Describes protocols of calling API service"""

    def call_api(self, method: str, params: Dict): ...


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

    def call_api(self, method: str, params: Dict):
        """调用消息通知API

        :raises MethodNotDefinedError: 当API方法未定义时
        :raises NotificationSendFailedError: 当API调用失败时
        """
        # 如果 API 网关上未注册该通知渠道，则跳过发送，不需要阻塞后续流程所以返回 True
        if not hasattr(self.client, method):
            raise MethodNotDefinedError(f"{method} is not registered on API Gateway")

        try:
            result = getattr(self.client, method)(json=params)
        except (APIGatewayResponseError, ResponseError) as e:
            logging.exception("call bk_cmsi api error, method: %s, params: %s", method, params)
            raise NotificationSendFailedError(f"API request failed: {e}") from e

        logger.debug("call bk_cmsi api success, result:%s", result)


class BkCmsiEsbClient:
    """由 ESB 提供的消息通知 API"""

    def __init__(self):
        # ESB 开启了免用户认证，但限制用户名不能为空，因此给默认用户名
        # 调用 ESB 需要使用特殊的应用 ID ，不是默认的 settings.BK_APP_CODE
        esb_client = get_client_by_username(
            "admin", bk_app_code=settings.BKAUTH_TOKEN_APP_CODE, bk_app_secret=settings.BKAUTH_TOKEN_SECRET_KEY
        )
        self.client = esb_client.api

    def call_api(self, method: str, params: Dict):
        """调用消息通知API

        :raises MethodNotDefinedError: 当API方法未定义时
        :raises NotificationSendFailedError: 当API调用失败时
        """
        if not hasattr(self.client, method):
            raise MethodNotDefinedError(f"{method} is not registered on ESB")

        try:
            result = getattr(self.client, method)(json=params)
        except Exception as e:
            raise NotificationSendFailedError(f"API request failed: {e}") from e

        # ESB 不管调用成功与否，状态码都会返回 200，需要通过 result 字段判断是否成功
        if not result.get("result"):
            logger.error("Call bk_cmsi api returned failure, result: %s", result)
            raise NotificationSendFailedError(f"API returned failure: {result.get('message', 'unknown error')}")


def make_bk_cmsi_client(tenant_id: str, stage: str = "prod") -> BkCmsiBackend:
    """按是否为多租户模式选择对应消息通知 API

    :param tenant_id: 租户ID。多租户模式下，消息的接收人必须在该租户下
    :param stage: 网关环境，默认为正式环境
    """
    # NOTE：先不添加单独的配置项来判断消息通知是否使用 API 网关的 API ，目前 APIGW 上的 bk-cmsi 网关是专门为多租户定制
    if settings.ENABLE_MULTI_TENANT_MODE:
        return BkCmsiApiGwClient(tenant_id, stage)
    else:
        return BkCmsiEsbClient()


class BkNotificationService:
    """蓝鲸消息通知服务，包含以下通知渠道：
    - 邮件通知
    - 企业微信通知（仅在上云版支持)
    - 微信通知
    - 短信通知

    通过 settings.BK_CMSI_ENABLED_METHODS 配置支持的通知渠道，例如：['send_mail', 'send_weixin']
    未配置的渠道将仅记录日志但不真实发送通知
    """

    def __init__(self, tenant_id: str, stage: str = "prod"):
        self.client = make_bk_cmsi_client(tenant_id, stage)
        # 从配置获取支持的通知方法列表，默认为空列表
        self.enabled_methods = getattr(settings, "BK_CMSI_ENABLED_METHODS", [])

    def safe_call_api(self, method: str, params: dict):
        """统一处理发送通知的边界，以下 2 种情况并不抛出异常：
        1. API 方法并未在 ESB 或者 API 网关上定义
        2. 配置项中 BK_CMSI_ENABLED_METHODS 中未配置该方法
        """
        if method not in self.enabled_methods:
            logger.warning("CMSI method %s is not enabled, skip: params:%s", method, params)
            return

        try:
            self.client.call_api(method, params)
        except MethodNotDefinedError:
            logger.warning("CMSI %s is not registered, skip sending notifications, params: %s", method, params)
            return
        except Exception:
            raise

    def send_mail(self, receivers: List[str], content: str, title: str):
        """发送邮件通知

        :param receivers: 接收人列表
        :param content: 邮件内容
        :param title: 邮件主题
        """
        if not receivers:
            raise InvalidNotificationParams("The receivers is empty")

        params = {
            "content": content,
            "title": title,
            "receiver__username": receivers,
        }
        return self.safe_call_api("send_mail", params)

    def send_weixin(self, receivers: List[str], content: str, title: str):
        """发送微信通知

        :param receivers: 接收人列表
        :param content: 通知文字
        :param title: 通知头部文字
        """
        if not receivers:
            raise InvalidNotificationParams("The receivers is empty")

        params = {
            "data": {"heading": title, "message": content},
            "receiver__username": receivers,
        }
        return self.safe_call_api("send_weixin", params)

    def send_wecom(self, receivers: List[str], content: str, title: str):
        """发送 WeCom(企业微信) 通知
        NOTE：目前仅上云版 ESB API 支持，其他版本调用会抛出 BaseNotifierError 异常

        :param receivers: 接收人列表
        :param content: 通知内容正文
        :param title: 通知标题
        """
        if not receivers:
            raise InvalidNotificationParams("The receivers is empty")

        params = {
            "content": content,
            "title": title,
            "receiver__username": receivers,
        }
        return self.safe_call_api("send_rtx", params)

    def send_sms(self, receivers: List[str], content: str):
        """发送短信通知

        :param receivers: 接收人列表
        :param content: 通知内容正文，如果是使用腾讯云等通道需要提前配置好通知模板
        """
        if not receivers:
            raise InvalidNotificationParams("The receivers is empty")

        params = {
            "receiver__username": receivers,
            "content": content,
        }
        return self.safe_call_api("send_sms", params)
