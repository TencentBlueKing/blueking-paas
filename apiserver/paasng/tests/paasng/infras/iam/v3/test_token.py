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
from typing import Any, Tuple
from unittest.mock import Mock

import pytest

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v3 import token as v3_token

TENANT_ID = "tenant-foo"

SYSTEM_TOKEN = "fake-system-token"


@pytest.fixture()
def stub_get_token(monkeypatch):
    """把 SDK 的取令牌调用换成桩

    :returns: 记录调用参数的 Mock，可断言实际查询的系统标识
    """

    def _stub(result: Any) -> Mock:
        get_token = Mock(side_effect=result) if isinstance(result, Exception) else Mock(return_value=result)
        monkeypatch.setattr(v3_token, "IAM", lambda *args, **kwargs: SimpleNamespace(get_token=get_token))

        return get_token

    return _stub


class TestFetchSystemToken:
    def test_returns_token_from_sdk(self, stub_get_token):
        """按平台自身的系统标识查询"""
        get_token = stub_get_token((True, "success", SYSTEM_TOKEN))

        assert v3_token.fetch_system_token(TENANT_ID) == SYSTEM_TOKEN

        get_token.assert_called_once_with(get_paas_system_id())

    def test_sdk_failure_is_converted_to_gateway_error(self, stub_get_token):
        """SDK 以返回值而非异常表达失败，须收敛成与 V4 一致的异常"""
        stub_get_token((False, "iam api fail", ""))

        with pytest.raises(BKIAMGatewayServiceError):
            v3_token.fetch_system_token(TENANT_ID)

    @pytest.mark.parametrize(
        "result",
        [
            # SDK 取字段带了默认值，缺 token 键给空串、值为 null 给 None
            pytest.param((True, "success", ""), id="empty-token"),
            pytest.param((True, "success", None), id="null-token"),
            pytest.param((True, "success", 123), id="non-str-token"),
        ],
    )
    def test_unusable_token_raises(self, stub_get_token, result: Tuple):
        """ok 为真但令牌不可用时必须报错

        空串会与不带密码的 Basic 凭证比中，等于凭一次异常响应就通过了认证。
        """
        stub_get_token(result)

        with pytest.raises(BKIAMGatewayServiceError):
            v3_token.fetch_system_token(TENANT_ID)
