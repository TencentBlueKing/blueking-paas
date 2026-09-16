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

from types import SimpleNamespace
from typing import Any, Dict, List, Union
from unittest.mock import Mock

import pytest
from bkapi_client_core.exceptions import HTTPResponseError

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4 import token as v4_token
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

TENANT_ID = "tenant-foo"

AUTH_TOKEN = "fake-auth-token"


class StubOperation:
    """记录调用参数的桩 Operation"""

    def __init__(self, responses: Union[List[Any], Exception]):
        self.name = "retrieve_system_auth_token"
        self.responses = responses
        self.calls: List[Dict] = []

    def __call__(self, **kwargs) -> Dict:
        self.calls.append(kwargs)
        if isinstance(self.responses, Exception):
            raise self.responses
        return self.responses.pop(0)


@pytest.fixture()
def stub_token_api(monkeypatch):
    """把取令牌的网关调用换成桩

    :returns: 桩 Operation，可在用例中断言实际发出的请求
    """

    def _stub(response: Any) -> StubOperation:
        op = StubOperation(response if isinstance(response, Exception) else [response])

        # 仍使用真实的基座，以便一并验证 header 注入与错误收敛
        client = BKIAMV4BaseClient(TENANT_ID)
        client.client = SimpleNamespace(retrieve_system_auth_token=op)  # type: ignore[assignment]
        monkeypatch.setattr(v4_token, "BKIAMV4BaseClient", lambda tenant_id: client)

        return op

    return _stub


class TestFetchSystemToken:
    def test_sends_expected_request(self, stub_token_api):
        """按平台自身的系统标识查询，取响应中的 auth_token"""
        op = stub_token_api({"data": {"auth_token": AUTH_TOKEN}})

        assert v4_token.fetch_system_token(TENANT_ID) == AUTH_TOKEN

        assert op.calls[0]["path_params"] == {"system_id": get_paas_system_id()}

    @pytest.mark.parametrize(
        "response",
        [
            pytest.param({"data": {}}, id="no-auth-token-field"),
            pytest.param({}, id="no-data-field"),
            pytest.param({"data": {"auth_token": None}}, id="null-token"),
            pytest.param({"data": {"auth_token": ""}}, id="empty-token"),
            pytest.param({"data": {"auth_token": 123}}, id="non-str-token"),
        ],
    )
    def test_unusable_token_raises(self, stub_token_api, response):
        """取不到可用令牌必须报错

        返回空串会被调用方拿去与请求里的密码做相等比较，不带密码的 Basic 凭证恰好比中，
        等于凭一次异常响应就通过了认证。
        """
        stub_token_api(response)

        with pytest.raises(BKIAMGatewayServiceError):
            v4_token.fetch_system_token(TENANT_ID)

    def test_api_failure_is_converted_to_gateway_error(self, stub_token_api):
        """接口失败由基座收敛为平台异常，调用方只需认一种失败形态"""
        stub_token_api(HTTPResponseError("boom", response=Mock(status_code=500, headers={})))

        with pytest.raises(BKIAMGatewayServiceError):
            v4_token.fetch_system_token(TENANT_ID)
