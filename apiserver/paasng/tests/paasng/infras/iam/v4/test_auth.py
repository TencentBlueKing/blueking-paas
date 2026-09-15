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
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
import requests
from bkapi_client_core.exceptions import HTTPResponseError

from paasng.infras.iam.base.constants import V4_OPERATOR_HEADER
from paasng.infras.iam.base.dto import AuthResource
from paasng.infras.iam.exceptions import BKIAMApiHTTPError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.auth import BKIAMV4AuthBackend
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

TENANT_ID = "tenant-foo"
USERNAME = "user-0"

# 资源实例上的 system 刻意不取配置里的默认值（即 get_paas_system_id() 的返回值）。
# 两者相等时，「资源相关取 resources[0].system、资源无关取平台系统 ID」这两条分支
# 即便被写反，断言也照样成立
SYSTEM_ID = "bk_iam_stub_system"


class StubOperation:
    """记录调用参数的桩 Operation，用于验证鉴权实现发出的请求"""

    def __init__(self, name: str, responses: List[Any] | Exception):
        self.name = name
        self.responses = responses
        self.calls: List[Dict] = []

    def __call__(self, **kwargs) -> Dict:
        self.calls.append(kwargs)

        # 传入单个异常表示每次调用都失败；放在列表里则表示指定的那一批失败
        if isinstance(self.responses, Exception):
            raise self.responses

        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp

        return resp


class StubClientBackend(BKIAMV4AuthBackend):
    """把网关 Operation 换成桩的鉴权实现

    仍复用真实的 BKIAMV4BaseClient，以便一并验证 header 注入、分批与错误转换。
    """

    def __init__(self, base_client: BKIAMV4BaseClient):
        self.base_client = base_client

    def _make_client(self, tenant_id: str) -> BKIAMV4BaseClient:
        return self.base_client


@pytest.fixture()
def make_backend():
    """构造鉴权实现，按 Operation 名指定各自的桩响应

    :returns: (backend, ops) —— ops 上按 Operation 名可取到桩，用于断言实际发出的请求
    """

    def _make(**responses: List[Any] | Exception):
        ops = SimpleNamespace(**{name: StubOperation(name, resp) for name, resp in responses.items()})

        base_client = BKIAMV4BaseClient(TENANT_ID)
        # client 是 __init__ 中赋的普通实例属性，可直接替换为桩。
        # 桩只提供当前用例会调用到的那几个 Operation，不满足 Group 的类型约束
        base_client.client = ops  # type: ignore[assignment]

        return StubClientBackend(base_client), ops

    return _make


def make_resources(*res_ids: str) -> List[AuthResource]:
    return [AuthResource(SYSTEM_ID, "application", res_id) for res_id in res_ids]


def action_flags(flags: Dict[str, bool]) -> Dict:
    """构造 auth-by-actions 的响应体"""
    return {"data": [{"action_id": action_id, "allowed": allowed} for action_id, allowed in flags.items()]}


def resource_flags(flags: Dict[str, bool]) -> Dict:
    """构造 auth-by-resources 的响应体"""
    return {"data": [{"resource_id": res_id, "allowed": allowed} for res_id, allowed in flags.items()]}


def make_http_error(status_code: int = 400, body: Dict | None = None) -> HTTPResponseError:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body or {}).encode()
    return HTTPResponseError("bad request", response=response)


class TestSingleAuth:
    def test_sends_expected_request(self, make_backend):
        """单资源单操作走 direct_auth，请求体带 subject / action_id / resource"""
        backend, ops = make_backend(direct_auth=[{"data": {"allowed": True}}])

        assert backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resources("app-1")) is True

        call = ops.direct_auth.calls[0]
        assert call["data"] == {
            "subject": {"type": "user", "id": USERNAME},
            "action_id": "view_basic_info",
            "resource": {"id": "app-1"},
        }
        # 带资源实例时，系统标识取自资源而不是平台默认值
        assert call["path_params"] == {"system_id": SYSTEM_ID}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [({"allowed": True}, True), ({"allowed": False}, False), ({}, False)],
    )
    def test_reads_allowed_flag(self, make_backend, data, expected):
        """响应未给出判定结果时按未授权处理，不得放行"""
        backend, _ = make_backend(direct_auth=[{"data": data}])

        assert (
            backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resources("app-1")) is expected
        )

    def test_resource_type_allowed_omits_resource(self, make_backend):
        """资源无关的操作不能带 resource 字段，否则权限中心会按资源相关的语义校验"""
        backend, ops = make_backend(direct_auth=[{"data": {"allowed": True}}])

        assert backend.resource_type_allowed(USERNAME, TENANT_ID, "create_application") is True

        call = ops.direct_auth.calls[0]
        assert "resource" not in call["data"]

        # 没有资源可依据时回落到平台自身的系统 ID，而不是沿用资源实例上的那个
        assert call["path_params"] == {"system_id": get_paas_system_id()}
        assert call["path_params"]["system_id"] != SYSTEM_ID

    def test_rejects_multiple_resources(self, make_backend):
        """单次鉴权只接受一个资源实例，多传时报错而非静默取首个"""
        backend, ops = make_backend(direct_auth=[])

        with pytest.raises(ValueError, match="at most one resource"):
            backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resources("app-1", "app-2"))

        assert ops.direct_auth.calls == []


class TestMultiActionsAuth:
    def test_single_call_within_limit(self, make_backend):
        """单资源多操作走 direct_auth_by_actions，一次请求判定全部操作"""
        backend, ops = make_backend(
            direct_auth_by_actions=[action_flags({"manage_members": True, "edit_basic_info": False})]
        )

        perms = backend.resource_inst_multi_actions_allowed(
            USERNAME, TENANT_ID, ["manage_members", "edit_basic_info"], make_resources("app-1")
        )

        assert perms == {"manage_members": True, "edit_basic_info": False}
        assert len(ops.direct_auth_by_actions.calls) == 1

        call = ops.direct_auth_by_actions.calls[0]
        assert call["data"]["resource"] == {"id": "app-1"}
        # 鉴权是读操作，批量调用不应带上写操作人 header
        assert V4_OPERATOR_HEADER not in call["headers"]

    def test_splits_beyond_batch_limit(self, make_backend):
        """25 个操作应拆为 20 + 5 两次调用，合并后返回 25 个判定结果"""
        action_ids = [f"action-{i}" for i in range(25)]
        backend, ops = make_backend(
            direct_auth_by_actions=[
                action_flags(dict.fromkeys(action_ids[:20], True)),
                action_flags(dict.fromkeys(action_ids[20:], False)),
            ]
        )

        perms = backend.resource_inst_multi_actions_allowed(USERNAME, TENANT_ID, action_ids, make_resources("app-1"))

        assert [len(call["data"]["action_ids"]) for call in ops.direct_auth_by_actions.calls] == [20, 5]
        assert len(perms) == 25
        assert all(perms[action_id] for action_id in action_ids[:20])
        assert not any(perms[action_id] for action_id in action_ids[20:])

    def test_missing_entry_is_denied(self, make_backend):
        """权限中心漏返回某个操作时按未授权处理，不能在取值处变成放行"""
        backend, _ = make_backend(direct_auth_by_actions=[action_flags({"manage_members": True})])

        perms = backend.resource_inst_multi_actions_allowed(
            USERNAME, TENANT_ID, ["manage_members", "edit_basic_info"], make_resources("app-1")
        )

        assert perms == {"manage_members": True, "edit_basic_info": False}


class TestBatchResourceMultiActionsAuth:
    def test_splits_by_action_dimension(self, make_backend):
        """3 资源 × 2 操作按 action 维度拆为 2 次调用，返回完整的 6 项判定结果"""
        backend, ops = make_backend(
            direct_auth_by_resources=[
                resource_flags({"app-1": True, "app-2": False, "app-3": True}),
                resource_flags({"app-1": False, "app-2": False, "app-3": True}),
            ]
        )

        perms = backend.batch_resource_multi_actions_allowed(
            USERNAME, TENANT_ID, ["view_basic_info", "basic_develop"], make_resources("app-1", "app-2", "app-3")
        )

        calls = ops.direct_auth_by_resources.calls
        assert [call["data"]["action_id"] for call in calls] == ["view_basic_info", "basic_develop"]
        assert calls[0]["data"]["resources"] == [{"id": "app-1"}, {"id": "app-2"}, {"id": "app-3"}]
        # 鉴权是读操作，批量调用不应带上写操作人 header
        assert V4_OPERATOR_HEADER not in calls[0]["headers"]

        assert perms == {
            "app-1": {"view_basic_info": True, "basic_develop": False},
            "app-2": {"view_basic_info": False, "basic_develop": False},
            "app-3": {"view_basic_info": True, "basic_develop": True},
        }

    def test_splits_resources_beyond_batch_limit(self, make_backend):
        """单个操作下 25 个资源应拆为 20 + 5 两次调用"""
        res_ids = [f"app-{i}" for i in range(25)]
        backend, ops = make_backend(
            direct_auth_by_resources=[
                resource_flags(dict.fromkeys(res_ids[:20], True)),
                resource_flags(dict.fromkeys(res_ids[20:], True)),
            ]
        )

        perms = backend.batch_resource_multi_actions_allowed(
            USERNAME, TENANT_ID, ["view_basic_info"], make_resources(*res_ids)
        )

        assert [len(call["data"]["resources"]) for call in ops.direct_auth_by_resources.calls] == [20, 5]
        assert len(perms) == 25
        assert all(perm["view_basic_info"] for perm in perms.values())


class TestFailureIsNotFallbackToAllow:
    def test_single_auth_error_carries_request_id(self, make_backend):
        """网关返回非 2xx 时抛出携带 request_id 的错误，不吞异常、不默认放行"""
        backend, _ = make_backend(
            direct_auth=make_http_error(
                body={
                    "request_id": "req-err",
                    "error": {"code": "INVALID_REQUEST", "message": "action(view_basic_info) not found"},
                }
            )
        )

        with pytest.raises(BKIAMApiHTTPError) as exc_info:
            backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resources("app-1"))

        assert exc_info.value.request_id == "req-err"
        assert exc_info.value.status_code == 400
        # V4 的错误码与描述嵌在 error 对象内，需被解析进异常消息便于排查
        assert "INVALID_REQUEST" in str(exc_info.value)
        assert "action(view_basic_info) not found" in str(exc_info.value)

    def test_batch_failure_aborts_whole_judgement(self, make_backend):
        """分批中任一批失败即整体失败，不以部分结果作为最终判定"""
        action_ids = [f"action-{i}" for i in range(25)]
        backend, ops = make_backend(
            direct_auth_by_actions=[
                action_flags(dict.fromkeys(action_ids[:20], True)),
                make_http_error(status_code=500),
            ]
        )

        with pytest.raises(BKIAMApiHTTPError):
            backend.resource_inst_multi_actions_allowed(USERNAME, TENANT_ID, action_ids, make_resources("app-1"))

        assert len(ops.direct_auth_by_actions.calls) == 2
