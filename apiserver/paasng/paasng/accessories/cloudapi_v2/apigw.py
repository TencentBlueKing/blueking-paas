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

"""bk-apigateway v2 网关客户端的公共实现"""

import json

from bkapi_client_core.apigateway import APIGatewayClient, Operation
from bkapi_client_core.client import ResponseHeadersRepresenter
from bkapi_client_core.exceptions import HTTPResponseError
from requests import Response
from requests.exceptions import HTTPError


class BkApigatewayClient(APIGatewayClient):
    """bk-apigateway 客户端基类

    子类只需定义 api = bind_property(Group, name="api").
    """

    _api_name = "bk-apigateway"

    def _handle_response_content(
        self,
        operation: Operation,
        response: Response | None,
    ):
        # 覆写父类方法, 接受非 JSON 类型的响应 对应网关 v2 响应格式
        if response is None:
            return None

        self.check_response_apigateway_error(response)

        try:
            response.raise_for_status()
        except HTTPError as err:
            response_headers_representer = ResponseHeadersRepresenter(response.headers)
            raise HTTPResponseError(
                "Error responded by Backend api, %s" % str(err),
                response=response,
                response_headers_representer=response_headers_representer,
            )

        try:
            return response.json()
        except (TypeError, json.JSONDecodeError):
            return response.text
