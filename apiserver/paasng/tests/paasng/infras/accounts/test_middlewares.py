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

from dataclasses import dataclass
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone as dj_timezone
from rest_framework.test import APIRequestFactory

from paasng.infras.accounts.middlewares import UserTimezoneMiddleware

request_factory = APIRequestFactory(enforce_csrf_checks=False)


def get_response(request):
    """Dummy response callback for middleware"""
    return mock.MagicMock()


@dataclass
class MockUser:
    """Mock user object for testing"""

    username: str
    time_zone: str | None = None
    is_authenticated: bool = True


@dataclass
class MockUserWithoutTimezone:
    """Mock user without timezone object for testing"""

    username: str
    is_authenticated: bool = True


class TestUserTimezoneMiddleware:
    """Test cases for UserTimezoneMiddleware"""

    def test_anonymous_user_skipped(self):
        """Test that anonymous users are skipped"""
        request = request_factory.get("/")
        request.user = AnonymousUser()

        middleware = UserTimezoneMiddleware(get_response)
        middleware.process_request(request)

        assert dj_timezone.get_current_timezone() == dj_timezone.get_default_timezone()

    @pytest.mark.parametrize(
        ("tz_name", "expected_activated"),
        [
            ("Asia/Shanghai", True),
            ("America/New_York", True),
            ("UTC", True),
            ("", False),
            (None, False),
            ("Invalid/Zone", False),
        ],
    )
    def test_timezone_activation(self, tz_name, expected_activated):
        """Test timezone activation with various values"""
        request = request_factory.get("/")
        request.user = MockUser(username="testuser", time_zone=tz_name)

        middleware = UserTimezoneMiddleware(get_response)
        middleware.process_request(request)

        current_tz = dj_timezone.get_current_timezone()
        if expected_activated:
            assert current_tz == ZoneInfo(tz_name)
        else:
            assert current_tz == dj_timezone.get_default_timezone()

    def test_user_without_timezone_attr(self):
        """Test fallback when user has no time_zone attribute"""
        request = request_factory.get("/")
        request.user = MockUserWithoutTimezone(username="testuser")

        middleware = UserTimezoneMiddleware(get_response)
        middleware.process_request(request)

        assert dj_timezone.get_current_timezone() == dj_timezone.get_default_timezone()

    def test_process_response_deactivates_timezone(self):
        """Test that process_response resets timezone"""
        request = request_factory.get("/")
        request.user = MockUser(username="testuser", time_zone="Asia/Tokyo")

        middleware = UserTimezoneMiddleware(get_response)
        middleware.process_request(request)
        assert dj_timezone.get_current_timezone() == ZoneInfo("Asia/Tokyo")

        mock_response = mock.MagicMock()
        result = middleware.process_response(request, mock_response)

        assert result == mock_response
        assert dj_timezone.get_current_timezone() == dj_timezone.get_default_timezone()
