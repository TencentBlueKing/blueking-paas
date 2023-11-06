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
import json
from typing import Dict
from unittest import mock

import pytest
from bkapi_client_core.exceptions import ResponseError
from blue_krill.web.std_error import APIError
from requests.models import Response

from paasng.bk_plugins.pluginscenter.thirdparty import market

pytestmark = pytest.mark.django_db


def make_response(data: Dict) -> Response:
    response = Response()
    response._content = json.dumps(data).encode()
    response.status_code = 400
    return response


@pytest.mark.parametrize(
    "exception, expected_exception",
    [
        (Exception(), APIError(code="UnknownError", message="system error")),
        (ResponseError(response=make_response({})), APIError(code="APIError", message="[invalid response body]")),
        (ResponseError(response=make_response({"message": "错误信息"})), APIError(code="APIError", message="错误信息")),
        (
            ResponseError(
                response=make_response({"message": "错误信息"}),
                response_headers_representer=mock.MagicMock(request_id="foo"),
            ),
            APIError(code="APIError", message="<request_id: foo> 错误信息"),
        ),
        (
            ResponseError(
                response=make_response({"detail": "错误信息"}),
                response_headers_representer=mock.MagicMock(request_id="foo"),
            ),
            APIError(code="APIError", message="<request_id: foo> 错误信息"),
        ),
    ],
)
def test_transform_exception(pd, plugin, exception, expected_exception):
    with mock.patch("bkapi_client_core.base.Operation.__call__") as call:
        call.side_effect = exception
        with pytest.raises(APIError) as exc:
            market.read_market_info(pd, plugin)
        assert exc.value.code == expected_exception.code
        assert exc.value.message == expected_exception.message
        assert exc.value.code_num == expected_exception.code_num
