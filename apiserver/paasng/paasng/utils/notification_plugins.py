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
from typing import Dict, List, Optional, Sequence, Tuple

import requests
from django.conf import settings
from django.utils.module_loading import import_string

from paasng.utils.notifier import UserNotificationPlugin, get_notification_backend

logger = logging.getLogger(__name__)


class BaseComponentAPIPlugin(UserNotificationPlugin):
    """Base class for notification plugins using component API"""

    def __init__(self):
        self.client = requests.session()
        self.inner_code, self.inner_secret = self._get_inner_auth_pair()
        self.url_prefix = "/api/c/compapi/v2/cmsi/"

    def get_common_params(self, bk_username: str):
        """
        Common parameters for calling BK API gateway

        The parameter (bk_username) is the username of the current user,
        and the application in the whitelist without login authentication is applied.
        Use this field to specify the current user.
        The default is the first receiver
        """
        return {
            "bk_username": bk_username,
            "app_code": self.inner_code,
            "app_secret": self.inner_secret,
        }

    def _call_api(self, method: str, bk_username: str, params: Dict) -> bool:
        """Send notification via BK API GateWay"""
        common_params = self.get_common_params(bk_username)
        url = f"{settings.COMPONENT_SYSTEM_HOST}{self.url_prefix}{method}/"
        try:
            resp = self.client.post(url, json={**common_params, **params})
            result = resp.json()
        except Exception:
            logger.exception("request to tof failed.")
            return False

        if result.get("result"):
            return True

        logger.warning(
            "send {method} to {receiver} failed: {code}/{reason}".format(
                method=method,
                receiver=params.get("receiver__username", "[unknown]"),
                code=result.get("code", "no exact code"),
                reason=result.get("message", "no exact reason"),
            )
        )
        return False

    @staticmethod
    def _get_inner_auth_pair() -> Tuple[str, str]:
        return settings.BKAUTH_TOKEN_APP_CODE, settings.BKAUTH_TOKEN_SECRET_KEY

    @staticmethod
    def cat_names(names: Sequence[str]) -> str:
        """Concatenate user names to call BK API GateWay API"""
        return ",".join(names)


class MailNotificationPlugin(BaseComponentAPIPlugin):
    """Send mail notification"""

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        if not receivers:
            logger.error("The receivers of sending mail is empty, skipped")
            return False

        params = {
            "content": content,
            "title": title,
            "receiver__username": self.cat_names(receivers),
        }
        bk_username = receivers[0]
        return self._call_api("send_mail", bk_username, params=params)


class WeComNotificationPlugin(BaseComponentAPIPlugin):
    """Send WeCom(企业微信) notification"""

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        if not receivers:
            logger.error("The receivers of sending rtx is empty, skipped")
            return False

        params = {
            "content": content,
            "title": title,
            "receiver__username": self.cat_names(receivers),
        }
        bk_username = receivers[0]
        return self._call_api("send_rtx", bk_username, params=params)


class WeChatNotificationPlugin(BaseComponentAPIPlugin):
    """Send WeChat notification"""

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        if not receivers:
            logger.error("The receivers of sending weixin is empty, skipped")
            return False

        params = {
            "data": content,
            "receiver__username": self.cat_names(receivers),
        }
        bk_username = receivers[0]
        return self._call_api("send_weixin", bk_username, params=params)


class SMSNotificationPlugin(BaseComponentAPIPlugin):
    """Send SMS notification"""

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        """Send SMS notification to user"""
        if not receivers:
            logger.error("The receivers of sending SMS is empty, skipped")
            return False

        params = {
            "receiver__username": receivers,
            "content": content,
        }
        bk_username = receivers[0]
        return self._call_api("send_sms", bk_username, params=params)


def register_plugins():
    """Register all notification plugins, this function should be executed after project started"""
    _backend = get_notification_backend()
    for backend_name, backend_cls in settings.NOTIFICATION_PLUGIN_CLASSES.items():
        _backend.register(backend_name, import_string(backend_cls)())
