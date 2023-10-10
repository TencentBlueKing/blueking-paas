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
import time

import pytest
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS

from paasng.core.core.storages.redisdb import get_default_redis
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import UserActionRateLimiter as UserActionFixedWindowRateLimiter
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user
from paasng.utils.rate_limit.token_bucket import UserActionRateLimiter as UserActionTokenBucketRateLimiter
from tests.utils.auth import create_user


@pytest.mark.parametrize('RateLimiter', [UserActionTokenBucketRateLimiter, UserActionFixedWindowRateLimiter])
def test_UserActionRateLimiter(RateLimiter):
    window_size, threshold = 3, 2
    user = create_user()
    rate_limiter = RateLimiter(get_default_redis(), user.username, UserAction.WATCH_PROCESS, window_size, threshold)
    # 消耗令牌
    for _ in range(threshold):
        assert rate_limiter.is_allowed()

    # 令牌桶满
    assert not rate_limiter.is_allowed()
    # 等待超时
    time.sleep(window_size)
    # 回收旧令牌并使用
    assert rate_limiter.is_allowed()


def test_rate_limits_on_view_func():
    window_size, threshold = 3, 2
    fake_request = HttpRequest()
    fake_request.user = create_user()

    class FakeViewSet:
        request = fake_request

        @rate_limits_by_user(UserAction.WATCH_PROCESS, window_size, threshold)
        def fake_view_func(self):
            return Response("ok")

    viewset = FakeViewSet()

    for _ in range(threshold):
        assert viewset.fake_view_func().status_code == HTTP_200_OK

    assert viewset.fake_view_func().status_code == HTTP_429_TOO_MANY_REQUESTS
    time.sleep(window_size)
    assert viewset.fake_view_func().status_code == HTTP_200_OK
