# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import translation

from paasng.utils.middlewares import BkLocaleMiddleware


@pytest.fixture(autouse=True)
def restore_language():
    """中间件会 activate 请求语言, 用例结束后还原, 避免污染同进程中后续用例"""
    yield
    translation.deactivate()


@pytest.fixture
def factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def middleware() -> BkLocaleMiddleware:
    return BkLocaleMiddleware(lambda request: HttpResponse())


class TestBkLocaleMiddleware:
    """语言只由 `blueking_language` cookie 决定, 缺失/非法时回退到默认语言."""

    @pytest.mark.parametrize(
        ("cookie", "expected"),
        [
            (None, "zh-cn"),  # cookie 缺失
            ("foo=bar", "zh-cn"),  # 无关 cookie 不影响语言
            ("blueking_language=en", "en"),
            ("blueking_language=en-us", "en"),  # 变体归一化为已支持的语言
            ("blueking_language=xx", "zh-cn"),  # 非法值
            ("blueking_language=", "zh-cn"),  # 空值
        ],
    )
    def test_language_resolution(
        self,
        factory: RequestFactory,
        middleware: BkLocaleMiddleware,
        cookie: str | None,
        expected: str,
    ):
        request = factory.get("/api/plat_mgt/applications/", **({"HTTP_COOKIE": cookie} if cookie else {}))
        middleware.process_request(request)

        assert translation.get_language() == expected
        assert getattr(request, "LANGUAGE_CODE") == expected

    def test_ignores_accept_language(self, factory: RequestFactory, middleware: BkLocaleMiddleware):
        """回归: 曾用 Django LocaleMiddleware, 会跟随 Accept-Language 返回英文"""
        request = factory.get("/api/", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
        middleware.process_request(request)

        assert translation.get_language() == "zh-cn"

    def test_response_headers(self, factory: RequestFactory, middleware: BkLocaleMiddleware):
        """响应需声明实际语言, 且缓存按 Cookie 区分而非 Accept-Language"""
        request = factory.get("/api/", HTTP_COOKIE="blueking_language=en")
        middleware.process_request(request)
        response = middleware.process_response(request, HttpResponse())

        assert response.headers["Content-Language"] == "en"
        assert "Cookie" in response.headers["Vary"]
        assert "Accept-Language" not in response.headers["Vary"]
