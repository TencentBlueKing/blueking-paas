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
    @pytest.fixture()
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
