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

import json
from unittest.mock import MagicMock, Mock

import pytest

from paasng.accessories.cloudapi_v2.apigateway.apigw.clients import Client


class TestClientHandleResponseContent:
    """Test Client._handle_response_content method"""

    @pytest.fixture()
    def client(self):
        """Create a Client instance for testing"""
        return Client(endpoint="http://example.com", stage="prod")

    def test_handle_204_no_content_response(self, client, mocker):
        """
        测试 client 在处理 204 No Content 响应时正常工作
        v2 网关的响应可能不为 JSON, 而 bkapi_client_core 默认会认为所有响应都是 JSON,
        故 patch 了 `_handle_response_content` 方法
        """
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        mocker.patch.object(client, "check_response_apigateway_error", return_value=None)

        result = client._handle_response_content(MagicMock(), mock_response)

        assert result == ""
