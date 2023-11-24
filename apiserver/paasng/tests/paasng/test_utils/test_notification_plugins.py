# -*- coding: utf-8 -*-
from unittest import mock

import pytest

from paasng.utils.notification_plugins import (
    BaseComponentAPIPlugin,
    MailNotificationPlugin,
    SMSNotificationPlugin,
    WeChatNotificationPlugin,
    WeComNotificationPlugin,
)


class TestPlugins:
    @pytest.fixture
    def mocked_call_api(self):
        with mock.patch.object(BaseComponentAPIPlugin, "_call_api") as mocked_call:
            yield mocked_call

    def test_mail(self, mocked_call_api):
        MailNotificationPlugin().send(["foo_user", "foo_user1"], "test_content", "test_title")
        assert mocked_call_api.call_args[0][0] == "send_mail"

    def test_sms(self, mocked_call_api):
        SMSNotificationPlugin().send(["foo_user", "foo_user1"], "test_content")
        assert mocked_call_api.call_args[0][0] == "send_sms"

    def test_wechat(self, mocked_call_api):
        WeChatNotificationPlugin().send(["foo_user", "foo_user1"], "test_content", "test_title")
        assert mocked_call_api.call_args[0][0] == "send_weixin"

    def test_wecom(self, mocked_call_api):
        WeComNotificationPlugin().send(["foo_user", "foo_user1"], "test_content", "test_title")
        assert mocked_call_api.call_args[0][0] == "send_rtx"
