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
import logging
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import pytest
import requests
from bkapi_client_core.exceptions import HTTPResponseError
from django.db.models import Q

from paasng.infras.iam.base.constants import V4_OPERATOR_HEADER
from paasng.infras.iam.base.dto import AuthResource
from paasng.infras.iam.exceptions import BKIAMApiHTTPError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4 import auth as v4_auth
from paasng.infras.iam.v4.auth import (
    V4_AUTHORIZED_IDS_WARN_THRESHOLD,
    V4_MALFORMED_REPR_LIMIT,
    V4_PUSHDOWN_RESOURCE_TYPE,
    BKIAMV4AuthBackend,
)
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

TENANT_ID = "tenant-foo"
USERNAME = "user-0"

# 策略下推用例统一使用的操作，即应用列表页的口径
PUSHDOWN_ACTION_ID = "view_basic_info"

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


def make_resource(res_id: str = "app-1") -> AuthResource:
    return AuthResource(SYSTEM_ID, "application", res_id)


def action_flags(flags: Dict[str, bool]) -> Dict:
    """构造 auth-by-actions 的响应体"""
    return {"data": [{"action_id": action_id, "allowed": allowed} for action_id, allowed in flags.items()]}


def make_http_error(status_code: int = 400, body: Optional[Dict] = None) -> HTTPResponseError:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body or {}).encode()
    return HTTPResponseError("bad request", response=response)


def make_authorized_resp(*entries: Dict) -> Dict:
    """构造 list_authorized_resource 的响应体"""
    return {"data": list(entries)}


def make_app_entry(ids: Any) -> Dict:
    """构造一条应用资源类型的授权条目

    ids 原样传入而不用变长参数，以便畸形响应的用例直接给出标量或含非字符串的列表。
    """
    return {"type": V4_PUSHDOWN_RESOURCE_TYPE, "ids": ids}


def collect_warnings(caplog) -> List[str]:
    """取出本次捕获的 warning 日志内容"""
    return [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]


@pytest.fixture()
def pushdown(make_backend, caplog):
    """按给定响应发起一次策略下推

    :param response: 桩响应；传入异常则表示该次调用失败
    :returns: (过滤条件, 本次产生的 warning 日志)
    """

    def _pushdown(response: Any, **kwargs) -> Tuple[Optional[Q], List[str]]:
        backend, _ = make_backend(list_authorized_resource=[response])

        with caplog.at_level(logging.WARNING, logger=v4_auth.logger.name):
            filters = backend.build_resource_filter(USERNAME, TENANT_ID, PUSHDOWN_ACTION_ID, **kwargs)

        return filters, collect_warnings(caplog)

    return _pushdown


class TestSingleAuth:
    def test_sends_expected_request(self, make_backend):
        """单资源单操作走 direct_auth，请求体带 subject / action_id / resource"""
        backend, ops = make_backend(direct_auth=[{"data": {"allowed": True}}])

        assert backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resource()) is True

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

        assert backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resource()) is expected

    def test_resource_type_allowed_omits_resource(self, make_backend):
        """资源无关的操作不能带 resource 字段，否则权限中心会按资源相关的语义校验"""
        backend, ops = make_backend(direct_auth=[{"data": {"allowed": True}}])

        assert backend.resource_type_allowed(USERNAME, TENANT_ID, "create_application") is True

        call = ops.direct_auth.calls[0]
        assert "resource" not in call["data"]

        # 没有资源可依据时回落到平台自身的系统 ID，而不是沿用资源实例上的那个
        assert call["path_params"] == {"system_id": get_paas_system_id()}
        assert call["path_params"]["system_id"] != SYSTEM_ID


class TestMultiActionsAuth:
    def test_single_call_within_limit(self, make_backend):
        """单资源多操作走 direct_auth_by_actions，一次请求判定全部操作"""
        backend, ops = make_backend(
            direct_auth_by_actions=[action_flags({"manage_members": True, "edit_basic_info": False})]
        )

        perms = backend.resource_inst_multi_actions_allowed(
            USERNAME, TENANT_ID, ["manage_members", "edit_basic_info"], make_resource()
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

        perms = backend.resource_inst_multi_actions_allowed(USERNAME, TENANT_ID, action_ids, make_resource())

        assert [len(call["data"]["action_ids"]) for call in ops.direct_auth_by_actions.calls] == [20, 5]
        assert len(perms) == 25
        assert all(perms[action_id] for action_id in action_ids[:20])
        assert not any(perms[action_id] for action_id in action_ids[20:])

    def test_missing_entry_is_denied(self, make_backend):
        """权限中心漏返回某个操作时按未授权处理，不能在取值处变成放行"""
        backend, _ = make_backend(direct_auth_by_actions=[action_flags({"manage_members": True})])

        perms = backend.resource_inst_multi_actions_allowed(
            USERNAME, TENANT_ID, ["manage_members", "edit_basic_info"], make_resource()
        )

        assert perms == {"manage_members": True, "edit_basic_info": False}

    @pytest.mark.parametrize("data", [{"action_id": "manage_members"}, ["manage_members"], None, 42])
    def test_malformed_data_is_denied(self, make_backend, data):
        """data 结构不符预期时按未授权处理，而不是在取值处抛异常变成 500"""
        backend, _ = make_backend(direct_auth_by_actions=[{"data": data}])

        perms = backend.resource_inst_multi_actions_allowed(
            USERNAME, TENANT_ID, ["manage_members", "edit_basic_info"], make_resource()
        )

        assert perms == {"manage_members": False, "edit_basic_info": False}


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
            backend.resource_inst_allowed(USERNAME, TENANT_ID, "view_basic_info", make_resource())

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
            backend.resource_inst_multi_actions_allowed(USERNAME, TENANT_ID, action_ids, make_resource())

        assert len(ops.direct_auth_by_actions.calls) == 2


class TestResourceFilterPushdown:
    """策略下推：V4 没有 SDK 的 make_filter，翻译逻辑由鉴权实现自己承担"""

    def test_sends_expected_request(self, make_backend):
        """按用户与操作查询，请求体不带资源实例"""
        backend, ops = make_backend(list_authorized_resource=[make_authorized_resp(make_app_entry(["app-1"]))])

        backend.build_resource_filter(USERNAME, TENANT_ID, PUSHDOWN_ACTION_ID)

        call = ops.list_authorized_resource.calls[0]
        assert call["data"] == {"subject": {"type": "user", "id": USERNAME}, "action_id": PUSHDOWN_ACTION_ID}
        # 请求体里没有资源实例可依据，系统标识只能回落到平台自身的
        assert call["path_params"] == {"system_id": get_paas_system_id()}
        # 下推是读操作，不应带上写操作人 header
        assert V4_OPERATOR_HEADER not in call["headers"]

    @pytest.mark.parametrize(
        ("entries", "expected_ids"),
        [
            pytest.param([make_app_entry(["app-foo", "app-bar"])], ["app-foo", "app-bar"], id="single-entry"),
            # 多条目取并集且去重保序：重复项既会无谓放大 IN 子句，也会让阈值日志虚高
            pytest.param(
                [make_app_entry(["app-foo", "app-bar"]), make_app_entry(["app-bar", "app-baz"])],
                ["app-foo", "app-bar", "app-baz"],
                id="merged-entries",
            ),
        ],
    )
    def test_specific_ids_become_in_filter(self, pushdown, entries, expected_ids):
        """具体的资源实例 ID 翻译为 code 的 IN 条件"""
        filters, warnings = pushdown(make_authorized_resp(*entries))

        assert filters == Q(code__in=expected_ids)
        # 正常返回不应产生任何 warning
        assert warnings == []

    def test_wildcard_becomes_always_true_filter(self, pushdown):
        """通配符授权产出恒真条件，且不再逐个枚举 ID

        取 `~Q(pk=None)` 而非空 Q()：调用方一律以 `if not filters` 判断有无策略，
        空 Q() 是 falsy，会让「全部可见」塌缩成豁免窗口。形态与 V3 SDK 的
        DjangoQuerySetConverter._any 保持一致。
        """
        filters, _ = pushdown(make_authorized_resp(make_app_entry(["app-foo", "*"])))

        assert filters == ~Q(pk=None)

    @pytest.mark.parametrize(
        "response",
        [
            pytest.param({"data": [make_app_entry([])]}, id="empty-ids"),
            pytest.param({"data": []}, id="empty-data"),
            pytest.param({}, id="no-data-field"),
        ],
    )
    def test_no_policy_returns_none(self, pushdown, response):
        """未取得可用策略时返回 None，与 V3 的 make_filter 在无策略时的返回一致

        不返回恒假条件，以便调用方走同一个豁免过滤器分支。
        """
        filters, _ = pushdown(response)

        assert filters is None

    def test_api_failure_returns_none_instead_of_raising(self, pushdown):
        """接口失败时记 warning 并返回 None，不上抛让列表页变成 500"""
        filters, warnings = pushdown(make_http_error(status_code=500, body={"request_id": "req-err"}))

        assert filters is None
        assert len(warnings) == 1
        assert PUSHDOWN_ACTION_ID in warnings[0]
        # 跨系统排查要靠权限中心的 request_id，日志里必须带上
        assert "req-err" in warnings[0]

    @pytest.mark.parametrize(
        ("entries", "expected"),
        [
            # 未知类型的 ID 不能混进应用的过滤条件
            pytest.param(
                [{"type": "bk_plugin", "ids": ["pd:p1"]}, make_app_entry(["app-foo"])],
                Q(code__in=["app-foo"]),
                id="unknown-type",
            ),
            # 别的资源类型上的通配符不得放通应用。这条守的是「有人把通配符判断提前到类型过滤
            # 之前」这类重构：那样改完插件的通配符授权会让用户看到全部应用，而其余用例仍全绿
            pytest.param(
                [{"type": "bk_plugin", "ids": ["*"]}, make_app_entry(["app-foo"])],
                Q(code__in=["app-foo"]),
                id="wildcard-on-other-type",
            ),
            # 畸形条目被跳过，同一响应里的合法条目照常生效
            pytest.param(
                ["not-an-object", make_app_entry(["app-foo"])], Q(code__in=["app-foo"]), id="malformed-with-valid"
            ),
            # 一条应用条目都没有，等同于未取得策略
            pytest.param([{"type": "bk_plugin", "ids": ["pd:p1", "*"]}], None, id="only-other-types"),
        ],
    )
    def test_unusable_entries_are_skipped_with_warning(self, pushdown, entries, expected):
        """无法使用的条目留痕后跳过，不猜测其语义"""
        filters, warnings = pushdown({"data": entries})

        assert filters == expected
        # 被跳过的内容按整次响应聚合成一条日志，不按条目刷屏
        assert len(warnings) == 1

    @pytest.mark.parametrize(
        "response",
        [
            # data 不是数组：真值标量直接迭代会抛 TypeError，字符串会被逐字符迭代
            pytest.param({"data": True}, id="data-not-iterable"),
            pytest.param({"data": "application"}, id="data-is-str"),
            # ids 不是字符串数组：整数抛 TypeError；字符串被 extend 逐字符展开，而单字符 code
            # 在平台内合法，等于凭畸形响应匹配到了未授权的应用
            pytest.param({"data": [make_app_entry(123)]}, id="ids-not-iterable"),
            pytest.param({"data": [make_app_entry("app-foo")]}, id="ids-is-str"),
            pytest.param({"data": [make_app_entry(["app-1", 2])]}, id="ids-has-non-str"),
            # 最危险的一种：extend("*") 得到 ["*"]，不校验类型就会命中通配符分支放通全部应用，
            # 那是整段实现里唯一一条会放宽可见范围的路径
            pytest.param({"data": [make_app_entry("*")]}, id="ids-is-wildcard-str"),
        ],
    )
    def test_malformed_response_yields_no_policy(self, pushdown, response):
        """响应结构与契约不符时按未取得策略处理

        这些形状都绕过了 `build_resource_filter` 只捕获 `BKIAMGatewayServiceError` 的收敛，
        不校验就会变成列表页 500 或错误的过滤条件。
        """
        filters, warnings = pushdown(response)

        assert filters is None
        assert len(warnings) == 1

    def test_malformed_log_is_length_bounded(self, pushdown):
        """畸形内容写日志时要截断，避免把整个响应体灌进单条日志"""
        payload = "x" * 10000

        _, warnings = pushdown({"data": [make_app_entry(payload)]})

        assert payload not in warnings[0]
        # 截断后的片段加上固定文案，总长仍应是常量级
        assert len(warnings[0]) < 2 * V4_MALFORMED_REPR_LIMIT

    def test_long_id_list_is_not_truncated(self, pushdown):
        """接口无分页参数，超长列表只留痕不截断，否则会静默少显应用"""
        res_ids = [f"app-{i}" for i in range(V4_AUTHORIZED_IDS_WARN_THRESHOLD + 500)]

        filters, warnings = pushdown(make_authorized_resp(make_app_entry(res_ids)))

        assert filters == Q(code__in=res_ids)
        assert len(warnings) == 1
        assert str(len(res_ids)) in warnings[0]

    def test_key_mapping_does_not_affect_result(self, make_backend):
        """key_mapping 是 V3 SDK converter 的概念，V4 下被忽略"""
        responses = [make_authorized_resp(make_app_entry(["app-foo"])) for _ in range(2)]
        backend, _ = make_backend(list_authorized_resource=responses)

        with_mapping = backend.build_resource_filter(
            USERNAME, TENANT_ID, PUSHDOWN_ACTION_ID, key_mapping={"application.id": "code"}
        )
        without_mapping = backend.build_resource_filter(USERNAME, TENANT_ID, PUSHDOWN_ACTION_ID)

        assert with_mapping == without_mapping

    def test_does_not_fall_back_to_per_resource_auth(self, make_backend):
        """下推只调一次列表接口，不得退化成逐条鉴权"""
        backend, ops = make_backend(
            list_authorized_resource=[make_authorized_resp(make_app_entry(["app-foo"]))],
            direct_auth=[],
            direct_auth_by_actions=[],
        )

        backend.build_resource_filter(USERNAME, TENANT_ID, PUSHDOWN_ACTION_ID)

        assert len(ops.list_authorized_resource.calls) == 1
        assert ops.direct_auth.calls == []
        assert ops.direct_auth_by_actions.calls == []
