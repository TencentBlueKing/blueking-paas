# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import List, Optional

from sentry_sdk import Client, Hub

logger = logging.getLogger(__name__)


class UserNotificationPlugin:
    """An object which sends notification to users"""

    name: str

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        """Send notification

        :param receivers: List of receiver usernames
        :param content: content of notification
        :param title: Optional title
        """
        raise NotImplementedError


class DummyUserNotificationPlugin(UserNotificationPlugin):
    """A dummy implementation of user notification plugin"""

    def send(self, receivers: List[str], content: str, title: Optional[str] = None) -> bool:
        logger.warning('Dummy notification backend invoked, receivers: %s', receivers)
        return True


class UserNotificationBackend:
    """Backend type for sending notifications to user"""

    def __init__(self):
        self._plugins = {}

    def register(self, name: str, plugin: UserNotificationPlugin):
        """Register a new plugin

        :param name:  the name of plugin
        """
        self._plugins[name] = plugin

    def __getattr__(self, plugin_name: str) -> UserNotificationPlugin:
        """Get a registed notification plugin"""
        try:
            return self._plugins[plugin_name]
        except KeyError:
            return DummyUserNotificationPlugin()


_notification_backend = UserNotificationBackend()


def get_notification_backend() -> UserNotificationBackend:
    """Get current notification backend instance"""
    return _notification_backend


def log_event_to_sentry(content: str, dsn: str):
    """mainly used for logging important event

    :param content: message
    :param dsn: sentry target
    :returns: True if sending success
    """
    try:
        client = Client(dsn=dsn, auto_enabling_integrations=False)
        Hub(client).capture_message(message=content)
    except Exception:
        logger.exception("sending sentry<{dsn}> failed".format(dsn=dsn))
        return False

    return True
