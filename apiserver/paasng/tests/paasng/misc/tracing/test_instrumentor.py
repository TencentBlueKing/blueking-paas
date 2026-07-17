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
import requests
import requests_mock
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from paasng.misc.tracing.instrumentor import requests_callback


class TestResponseHookIntegration:
    """回归测试: RequestsInstrumentor().instrument(response_hook=requests_callback)

    验证 OTel 0.64b0 的 response_hook 回调签名 (span, request, response)
    与 requests_callback 的 3 参数签名匹配, 不会抛出 TypeError.
    """

    @pytest.fixture(autouse=True)
    def _instrument(self):
        """启用 RequestsInstrumentor 并注入 requests_callback"""
        instrumentor = RequestsInstrumentor()
        instrumentor.instrument(response_hook=requests_callback)
        yield
        instrumentor.uninstrument()

    def test_application_json(self):
        """response_hook 三元组签名匹配, 不抛 TypeError"""
        with requests_mock.Mocker() as m:
            m.get("http://test/api", json={"code": 0}, headers={"Content-Type": "application/json"})

            resp = requests.get("http://test/api", timeout=1)
            assert resp.status_code == 200

    def test_application_json_with_charset(self):
        """Content-Type 带 charset 参数时正常解析, 不抛 TypeError"""
        with requests_mock.Mocker() as m:
            m.get(
                "http://test/api",
                json={"code": 0, "message": "ok"},
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

            resp = requests.get("http://test/api", timeout=1)
            assert resp.status_code == 200
            assert resp.json() == {"code": 0, "message": "ok"}

    def test_non_json_skipped(self):
        """非 JSON 响应正常返回, 不抛异常"""
        with requests_mock.Mocker() as m:
            m.get("http://test/healthz", text="OK", headers={"Content-Type": "text/plain"})

            resp = requests.get("http://test/healthz", timeout=1)
            assert resp.status_code == 200
            assert resp.text == "OK"

    def test_response_is_none_on_connection_error(self):
        """连接异常时 response_hook 收到 response=None, 不抛 TypeError"""
        with requests_mock.Mocker() as m:
            m.get("http://test/timeout", exc=ConnectionError)

            with pytest.raises(ConnectionError):
                requests.get("http://test/timeout", timeout=1)
