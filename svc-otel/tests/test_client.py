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

from unittest.mock import Mock, call

import pytest
from bkapi_client_core.exceptions import APIGatewayResponseError
from svc_otel.bkmonitorv3.client import BkMonitorBackend, BkMonitorClient
from svc_otel.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError


@pytest.fixture()
def backend():
    return Mock(spec=BkMonitorBackend)


@pytest.fixture()
def client(backend):
    return BkMonitorClient(backend)


class TestGetOrCreateApm:
    def test_reuse_existing_application(self, client, backend):
        """按应用名和空间查询已有 APM，直接返回 token，不调用创建接口。"""
        backend.detail_apm_application.return_value = {"result": True, "data": {"token": "existing-token"}}

        assert client.get_or_create_apm("bkapp_demo_stag", "bkpaas__demo") == "existing-token"
        backend.detail_apm_application.assert_called_once_with(
            data={"app_name": "bkapp_demo_stag", "space_uid": "bkpaas__demo"}
        )
        backend.apm_create_application.assert_not_called()

    def test_create_when_application_does_not_exist(self, client, backend):
        """查询提示应用不存在时，使用相同的应用名和空间创建 APM 并返回 token。"""
        backend.detail_apm_application.return_value = {"result": False, "message": "application does not exist"}
        backend.apm_create_application.return_value = {"result": True, "data": "created-token"}

        assert client.get_or_create_apm("bkapp_demo_stag", "bkpaas__demo") == "created-token"
        assert backend.mock_calls == [
            call.detail_apm_application(data={"app_name": "bkapp_demo_stag", "space_uid": "bkpaas__demo"}),
            call.apm_create_application(data={"app_name": "bkapp_demo_stag", "space_uid": "bkpaas__demo"}),
        ]

    def test_missing_token_does_not_trigger_create(self, client, backend):
        """查询成功但 token 为空时抛出异常，不尝试创建 APM。"""
        backend.detail_apm_application.return_value = {"result": True, "data": {"token": ""}}

        with pytest.raises(BkMonitorApiError, match="token is empty"):
            client.get_or_create_apm("bkapp_demo_stag", "bkpaas__demo")

        backend.apm_create_application.assert_not_called()

    def test_gateway_error_does_not_trigger_create(self, client, backend):
        """查询发生网关异常时抛出网关服务错误，不尝试创建 APM。"""
        backend.detail_apm_application.side_effect = APIGatewayResponseError("gateway error")

        with pytest.raises(BkMonitorGatewayServiceError, match="Failed to get APM"):
            client.get_or_create_apm("bkapp_demo_stag", "bkpaas__demo")

        backend.apm_create_application.assert_not_called()

    @pytest.mark.parametrize(
        ("response", "message"),
        [
            ({"result": False, "message": "应用名称已存在"}, "应用名称已存在"),
            ({"result": True, "data": ""}, "token is empty"),
        ],
    )
    def test_create_failure_is_propagated(self, client, backend, response, message):
        """创建返回名称冲突或空 token 时抛出相应异常，不重复查询或创建。"""
        backend.detail_apm_application.return_value = {"result": False, "message": "application does not exist"}
        backend.apm_create_application.return_value = response

        with pytest.raises(BkMonitorApiError, match=message):
            client.get_or_create_apm("bkapp_demo_stag", "bkpaas__demo")

        backend.detail_apm_application.assert_called_once()
        backend.apm_create_application.assert_called_once()
