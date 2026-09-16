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

import json
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock

import pytest
import requests
from bkapi_client_core.exceptions import (
    APIGatewayResponseError,
    EndpointNotSetError,
    HTTPResponseError,
    JSONResponseError,
    PathParamsMissing,
)

from paasng.infras.iam.base.constants import V4_OPERATOR_HEADER
from paasng.infras.iam.exceptions import BKIAMApiHTTPError, BKIAMGatewayServiceError
from paasng.infras.iam.v4.http import BKIAMV4BaseClient


class StubOperation:
    """记录调用参数的桩 Operation，用于验证客户端基座发出的请求"""

    def __init__(self, responses: Union[List[Any], Exception]):
        self.name = "stub_operation"
        self.responses = responses
        self.calls: List[Dict] = []

    def __call__(self, **kwargs) -> Dict:
        self.calls.append(kwargs)
        if isinstance(self.responses, Exception):
            raise self.responses
        return self.responses.pop(0)


def make_page(results: List[Dict], count: Optional[int] = None) -> Dict:
    data: Dict = {"results": results}
    if count is not None:
        data["count"] = count
    return {"data": data, "request_id": "req-ok"}


def make_json_response_error(status_code: int) -> JSONResponseError:
    """模拟 SDK 对空/非法 JSON 响应抛出的 JSONResponseError"""
    response = Mock()
    response.status_code = status_code
    response.headers = {}
    return JSONResponseError("The response is not a valid JSON", response=response)


@pytest.fixture()
def client() -> BKIAMV4BaseClient:
    return BKIAMV4BaseClient("tenant-foo", operator="someone")


class TestCall:
    """调用失败必须收敛为平台异常，调用方才能按「判定失败」统一处理"""

    def test_treats_204_empty_body_as_success(self, client):
        """update_* 成功返回 204 无 body。SDK 会抛 JSONResponseError，应视为写入成功。"""
        operation = StubOperation(make_json_response_error(204))

        assert client.call(operation) == {}

    def test_invalid_json_on_non_204_raises_gateway_error(self, client):
        operation = StubOperation(make_json_response_error(200))

        with pytest.raises(BKIAMGatewayServiceError, match="invalid json"):
            client.call(operation)

    def test_http_error_is_wrapped(self, client):
        """非 2xx 仍要抛出带状态码的 BKIAMApiHTTPError，不能被兜底分支吞成通用网关错误"""
        response = Mock(status_code=409, headers={})
        operation = StubOperation(HTTPResponseError("conflict", response=response))

        with pytest.raises(BKIAMApiHTTPError) as exc_info:
            client.call(operation)

        assert exc_info.value.status_code == 409

    def test_apigw_error_is_wrapped(self, client):
        operation = StubOperation(APIGatewayResponseError("gateway down"))

        with pytest.raises(BKIAMGatewayServiceError, match="gateway down"):
            client.call(operation)

    def test_wraps_connection_error(self, client):
        """权限中心不可达时不能把原始的 requests 异常漏出去，否则调用方的捕获会失效"""
        operation = StubOperation(requests.exceptions.ConnectionError("connection refused"))

        with pytest.raises(BKIAMGatewayServiceError, match="stub_operation"):
            client.call(operation)

    def test_wraps_read_timeout(self, client):
        operation = StubOperation(requests.exceptions.ReadTimeout("read timed out"))

        with pytest.raises(BKIAMGatewayServiceError):
            client.call(operation)

    @pytest.mark.parametrize(
        "exc",
        [
            pytest.param(EndpointNotSetError("endpoint not set"), id="endpoint-not-set"),
            pytest.param(PathParamsMissing("system_id missing"), id="path-params-missing"),
        ],
    )
    def test_wraps_bkapi_only_errors(self, client, exc):
        """只继承 BKAPIError 的异常也要收敛

        EndpointNotSetError 与 PathParamsMissing 不是 RequestException 的子类，
        漏掉它们会让网关地址未配置这类故障越过调用方的捕获，从「取不到策略」变成 500——
        而 V3 下同类配置错误经 SDK 的异常漏斗最终是前者。
        """
        operation = StubOperation(exc)

        with pytest.raises(BKIAMGatewayServiceError, match="stub_operation"):
            client.call(operation)


class TestOperatorHeader:
    def test_write_uses_instance_operator(self, client):
        operation = StubOperation([{"data": {}}])

        client.call(operation, for_write=True)

        assert operation.calls[0]["headers"][V4_OPERATOR_HEADER] == "someone"

    def test_write_uses_explicit_operator_without_mutating_instance(self, client):
        operation = StubOperation([{"data": {}}])

        client.call(operation, for_write=True, operator="someone-else")

        assert operation.calls[0]["headers"][V4_OPERATOR_HEADER] == "someone-else"
        assert client.operator == "someone"

    def test_read_omits_operator_header(self, client):
        operation = StubOperation([{"data": {}}])

        client.call(operation)

        assert V4_OPERATOR_HEADER not in operation.calls[0]["headers"]


class TestExtractErrorDetail:
    """错误体里的 code 与 message 要尽量拼进异常消息，缺项时不能拼出误导性的内容"""

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            (
                {"error": {"code": "INVALID_REQUEST", "message": "action not found"}},
                "INVALID_REQUEST: action not found",
            ),
            # 只给出一项时单独返回该项，不拼接出 "None: xxx" 这类内容
            ({"error": {"message": "action not found"}}, "action not found"),
            ({"error": {"code": "INVALID_REQUEST"}}, "INVALID_REQUEST"),
            # 两项都缺、error 不是对象、没有 error 字段：无可用信息，调用方只拼 SDK 的原始消息
            ({"error": {}}, None),
            ({"error": "invalid request"}, None),
            ({"request_id": "req-err"}, None),
        ],
    )
    def test_combines_code_and_message(self, body, expected):
        response = requests.Response()
        response.status_code = 400
        response._content = json.dumps(body).encode()

        assert BKIAMV4BaseClient._extract_error_detail(HTTPResponseError("bad request", response=response)) == expected

    def test_returns_none_without_response(self):
        assert BKIAMV4BaseClient._extract_error_detail(HTTPResponseError("bad request")) is None

    def test_returns_none_for_non_json_body(self):
        """网关返回 HTML 错误页时不应抛异常，取不到 detail 即可"""
        response = requests.Response()
        response.status_code = 502
        response._content = b"<html>502 Bad Gateway</html>"

        assert BKIAMV4BaseClient._extract_error_detail(HTTPResponseError("bad gateway", response=response)) is None


class TestPaginate:
    def test_fetches_all_pages_without_truncation(self, client):
        """250 条数据在单页上限 100 的约束下应发起 3 次调用并返回全部数据"""
        operation = StubOperation(
            [
                make_page([{"id": i} for i in range(100)], count=250),
                make_page([{"id": i} for i in range(100, 200)], count=250),
                make_page([{"id": i} for i in range(200, 250)], count=250),
            ]
        )

        results = list(client.paginate(operation))

        assert len(results) == 250
        assert [item["id"] for item in results] == list(range(250))
        assert len(operation.calls) == 3
        assert [call["params"]["page"] for call in operation.calls] == [1, 2, 3]
        assert {call["params"]["page_size"] for call in operation.calls} == {100}

    def test_stops_on_partial_page(self, client):
        operation = StubOperation([make_page([{"id": 1}], count=1)])

        assert len(list(client.paginate(operation))) == 1
        assert len(operation.calls) == 1

    def test_stops_without_count_field(self, client):
        """权限中心未返回总数时，以「本页未取满」判定结束"""
        operation = StubOperation([make_page([{"id": i} for i in range(100)]), make_page([{"id": 100}])])

        assert len(list(client.paginate(operation))) == 101
        assert len(operation.calls) == 2

    def test_keeps_extra_params(self, client):
        operation = StubOperation([make_page([], count=0)])

        list(client.paginate(operation, params={"name": "foo"}, page_size=50))

        assert operation.calls[0]["params"] == {"name": "foo", "page": 1, "page_size": 50}

    def test_rejects_page_size_beyond_limit(self, client):
        with pytest.raises(ValueError, match="exceeds the bkiam limit"):
            list(client.paginate(StubOperation([]), page_size=101))


class TestCallInBatches:
    def test_splits_by_batch_limit(self, client):
        """45 个条目应自动拆为 20 + 20 + 5 三次调用，且条目不丢失"""
        operation = StubOperation([{"data": {}} for _ in range(3)])
        usernames = [f"user-{i}" for i in range(45)]

        client.call_in_batches(operation, usernames, lambda batch: {"members": batch})

        batch_sizes = [len(call["data"]["members"]) for call in operation.calls]
        assert batch_sizes == [20, 20, 5]

        submitted = [name for call in operation.calls for name in call["data"]["members"]]
        assert submitted == usernames

    def test_single_call_within_limit(self, client):
        operation = StubOperation([{"data": {}}])

        client.call_in_batches(operation, ["user-0"], lambda batch: {"members": batch})

        assert len(operation.calls) == 1

    def test_no_call_for_empty_items(self, client):
        operation = StubOperation([])

        assert client.call_in_batches(operation, [], lambda batch: {"members": batch}) == []
        assert operation.calls == []

    def test_rejects_batch_size_beyond_limit(self, client):
        with pytest.raises(ValueError, match="exceeds the bkiam limit"):
            client.call_in_batches(StubOperation([]), [], lambda batch: batch, batch_size=21)
