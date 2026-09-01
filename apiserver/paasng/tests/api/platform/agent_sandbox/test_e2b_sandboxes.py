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


from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.e2b import sandboxes
from paasng.platform.agent_sandbox.e2b.exceptions import (
    E2BClusterUnavailable,
    E2BGatewayError,
    E2BGatewayTimeout,
    E2BGatewayUnavailable,
    E2BSandboxNotFound,
)
from paasng.platform.agent_sandbox.models import E2BApiKey

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SANDBOX_ID = "e2b-envd-20"
CREATE_URL = reverse("agent_sandbox.e2b.sandboxes.create")
LIST_URL = reverse("agent_sandbox.e2b.sandboxes.list")
DETAIL_URL = reverse("agent_sandbox.e2b.sandboxes.detail", kwargs={"sandbox_id": SANDBOX_ID})
TIMEOUT_URL = reverse("agent_sandbox.e2b.sandboxes.timeout", kwargs={"sandbox_id": SANDBOX_ID})


@pytest.fixture()
def e2b_client(bk_app, bk_user) -> APIClient:
    """带合法 X-API-Key 的客户端。

    不复用 api_client：那个走的是平台的登录态，而协议端点只认 API Key，
    用它反而会掩盖认证配错的问题。
    """
    _, plain_key = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.username)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=plain_key)
    return client


class TestAuthentication:
    def test_rejects_request_without_key(self):
        resp = APIClient().post(CREATE_URL, data={"templateID": "e2b-envd"}, format="json")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_error_body_matches_sdk_expectation(self):
        """SDK 只读 message 字段，且平台的 login_url 不能泄露给 e2b 客户端。"""
        resp = APIClient().get(LIST_URL)

        body = resp.json()
        assert set(body) == {"code", "message"}
        assert body["code"] == status.HTTP_401_UNAUTHORIZED


class TestCreate:
    def test_returns_gateway_response_unwrapped(self, e2b_client):
        """响应体就是网关那份报文，不能被平台的规范包装层套一层。"""
        payload = {"sandboxID": SANDBOX_ID, "domain": "e2b.example.com", "envdAccessToken": "tok"}

        with mock.patch.object(sandboxes, "create_sandbox", return_value=payload):
            resp = e2b_client.post(CREATE_URL, data={"templateID": "e2b-envd"}, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json() == payload

    def test_requires_template(self, e2b_client):
        resp = e2b_client.post(CREATE_URL, data={}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_forwards_full_request_body(self, e2b_client):
        """序列化器只认 templateID，但转发的必须是原始请求体。"""
        body = {"templateID": "e2b-envd", "timeout": 600, "metadata": {"owner": "a"}}

        with mock.patch.object(sandboxes, "create_sandbox", return_value={}) as create:
            e2b_client.post(CREATE_URL, data=body, format="json")

        assert create.call_args.args[1] == body


class TestList:
    def test_returns_bare_array(self, e2b_client):
        """e2b 的列表响应没有分页包装，套上 SDK 就反序列化不了。"""
        items = [{"sandboxID": SANDBOX_ID}]

        with mock.patch.object(sandboxes, "list_sandboxes", return_value=items):
            resp = e2b_client.get(LIST_URL)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == items


class TestRetrieveAndDestroy:
    def test_retrieve_returns_gateway_response(self, e2b_client):
        detail = {"sandboxID": SANDBOX_ID, "envdAccessToken": "refreshed"}

        with mock.patch.object(sandboxes, "get_sandbox", return_value=detail):
            resp = e2b_client.get(DETAIL_URL)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == detail

    def test_destroy_returns_no_content(self, e2b_client):
        with mock.patch.object(sandboxes, "kill_sandbox") as kill:
            resp = e2b_client.delete(DETAIL_URL)

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert kill.call_args.args[1] == SANDBOX_ID

    def test_set_timeout_requires_positive_value(self, e2b_client):
        resp = e2b_client.post(TIMEOUT_URL, data={"timeout": 0}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestErrorMapping:
    @pytest.mark.parametrize(
        ("exc", "expected_status"),
        [
            (E2BSandboxNotFound("gone"), status.HTTP_404_NOT_FOUND),
            (E2BGatewayTimeout("slow"), status.HTTP_408_REQUEST_TIMEOUT),
            (E2BGatewayError("boom"), status.HTTP_502_BAD_GATEWAY),
            (E2BGatewayUnavailable("down"), status.HTTP_503_SERVICE_UNAVAILABLE),
            (E2BClusterUnavailable("no cluster"), status.HTTP_503_SERVICE_UNAVAILABLE),
        ],
    )
    def test_maps_to_sdk_status_codes(self, e2b_client, exc, expected_status):
        with mock.patch.object(sandboxes, "create_sandbox", side_effect=exc):
            resp = e2b_client.post(CREATE_URL, data={"templateID": "e2b-envd"}, format="json")

        assert resp.status_code == expected_status
        assert resp.json() == {"code": expected_status, "message": mock.ANY}

    def test_does_not_leak_internal_details(self, e2b_client):
        """异常自带的信息里有集群名、网关地址这类内部拓扑，不该出现在响应里。"""
        exc = E2BClusterUnavailable("no cluster with e2b config for tenant acme in region ieod")

        with mock.patch.object(sandboxes, "create_sandbox", side_effect=exc):
            resp = e2b_client.post(CREATE_URL, data={"templateID": "e2b-envd"}, format="json")

        assert "acme" not in resp.content.decode()
