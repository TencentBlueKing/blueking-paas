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

"""网关客户端的 HTTP 层行为：路径拼装、凭证注入与失败分类。"""

import json

import pytest
import requests
import requests_mock

from paasng.platform.agent_sandbox.e2b.exceptions import (
    E2BGatewayError,
    E2BGatewayNotFound,
    E2BGatewayTimeout,
    E2BGatewayUnavailable,
)
from paasng.platform.agent_sandbox.e2b.gateway import E2BGatewayClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

GATEWAY_URL = "http://e2b-gateway.bcs-system:8080"


@pytest.fixture()
def client(e2b_config) -> E2BGatewayClient:
    return E2BGatewayClient(e2b_config)


@pytest.fixture()
def gateway_http():
    with requests_mock.Mocker() as m:
        yield m


def test_sends_gateway_credential(client, gateway_http):
    """用的是集群自己的真实凭证，不是用户那枚。"""
    gateway_http.get(f"{GATEWAY_URL}/v2/sandboxes", json=[])

    client.list_sandboxes()

    assert gateway_http.last_request.headers["X-API-Key"] == "e2b_real_gateway_key"


def test_create_posts_payload_verbatim(client, gateway_http):
    gateway_http.post(f"{GATEWAY_URL}/sandboxes", json={"sandboxID": "sbx-1"})

    assert client.create_sandbox({"templateID": "e2b-envd"}) == {"sandboxID": "sbx-1"}
    assert json.loads(gateway_http.last_request.body) == {"templateID": "e2b-envd"}


def test_escapes_sandbox_id_in_path(client, gateway_http):
    """沙箱 ID 来自网关，不对格式做假设，因此按 URL 组件转义后再拼。"""
    gateway_http.register_uri(requests_mock.ANY, requests_mock.ANY, json={})

    client.get_sandbox("a/b")

    assert gateway_http.last_request.url == f"{GATEWAY_URL}/sandboxes/a%2Fb"


def test_rejects_non_list_from_list_endpoint(client, gateway_http):
    """e2b 的列表响应是裸数组。收到别的形状说明对端不是预期的网关，早点失败。"""
    gateway_http.get(f"{GATEWAY_URL}/v2/sandboxes", json={"items": []})

    with pytest.raises(E2BGatewayError):
        client.list_sandboxes()


def test_404_is_distinguishable(client, gateway_http):
    """单列一类，好让调用方把销毁的 404 当成幂等成功。"""
    gateway_http.delete(f"{GATEWAY_URL}/sandboxes/sbx-1", status_code=404)

    with pytest.raises(E2BGatewayNotFound):
        client.kill_sandbox("sbx-1")


def test_other_http_errors_are_generic(client, gateway_http):
    gateway_http.get(f"{GATEWAY_URL}/sandboxes/sbx-1", status_code=500)

    with pytest.raises(E2BGatewayError) as exc_info:
        client.get_sandbox("sbx-1")

    assert not isinstance(exc_info.value, E2BGatewayNotFound)


def test_timeout_is_distinguishable(client, gateway_http):
    """与「连不上」分开：超时对外是 408 建议重试，连不上是 503。"""
    gateway_http.post(f"{GATEWAY_URL}/sandboxes", exc=requests.Timeout)

    with pytest.raises(E2BGatewayTimeout):
        client.create_sandbox({"templateID": "e2b-envd"})


def test_connection_error_maps_to_unavailable(client, gateway_http):
    gateway_http.get(f"{GATEWAY_URL}/v2/sandboxes", exc=requests.ConnectionError)

    with pytest.raises(E2BGatewayUnavailable):
        client.list_sandboxes()


def test_error_message_does_not_leak_gateway_body(client, gateway_http):
    """网关的响应体可能带凭证或其他租户的沙箱标识，不能进异常消息。"""
    gateway_http.get(f"{GATEWAY_URL}/v2/sandboxes", status_code=500, json={"secret": "e2b_leaked_key"})

    with pytest.raises(E2BGatewayError) as exc_info:
        client.list_sandboxes()

    assert "e2b_leaked_key" not in str(exc_info.value)
