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

from typing import Any, Dict, List, Optional, Union

import pytest

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


@pytest.fixture()
def client() -> BKIAMV4BaseClient:
    return BKIAMV4BaseClient("tenant-foo", operator="someone")


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
