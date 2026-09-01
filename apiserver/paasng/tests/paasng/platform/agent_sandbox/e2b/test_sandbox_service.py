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

"""控制面编排层的行为验证。

底层网关全程用替身，这里关心的是 apiserver 自己那部分：选集群、落库、回滚、
地址改写与归属判定。网关本身的 HTTP 行为在 test_gateway.py 里单独覆盖。
"""

import pytest
from django.db.utils import IntegrityError

from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.agent_sandbox.e2b import sandboxes
from paasng.platform.agent_sandbox.e2b.clusters import get_e2b_cluster_config
from paasng.platform.agent_sandbox.e2b.constants import E2BSandboxStatus
from paasng.platform.agent_sandbox.e2b.exceptions import (
    E2BGatewayNotFound,
    E2BGatewayUnavailable,
    E2BSandboxNotFound,
)
from paasng.platform.agent_sandbox.models import E2BSandbox
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .conftest import DATA_PLANE_ADDRESS, GATEWAY_INTERNAL_DOMAIN

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SANDBOX_ID = "e2b-envd-20"
ACCESS_TOKEN = "envd-token-issued-by-gateway"


def _create_response(sandbox_id: str = SANDBOX_ID, **overrides) -> dict:
    """参考真实网关创建响应的报文。

    其中 domain 是集群内 e2b 网关地址，apiserver 需要改写。
    """
    return {
        "templateID": "e2b-envd",
        "sandboxID": sandbox_id,
        "clientID": "bk",
        "startedAt": "2026-08-31T10:00:00Z",
        "endAt": "2026-08-31T11:00:00Z",
        "state": "running",
        "cpuCount": 2,
        "memoryMB": 4096,
        "diskSizeMB": 10240,
        "envdVersion": "0.2.4",
        "domain": GATEWAY_INTERNAL_DOMAIN,
        "envdAccessToken": ACCESS_TOKEN,
        **overrides,
    }


class FakeGateway:
    """网关替身。

    构造签名与真实客户端一致（接一个集群配置），因此可以整个顶替掉
    ``sandboxes`` 模块里的类引用；调用记录留在实例上供断言。
    """

    def __init__(self):
        self.create_response = _create_response()
        self.get_response = _create_response()
        self.list_response: list[dict] = []
        self.errors: dict[str, Exception] = {}
        self.configs = []
        self.created_payloads = []
        self.killed = []
        self.timeouts = []

    def __call__(self, config):
        self.configs.append(config)
        self.config = config
        return self

    def for_cluster(self, cluster_name: str):
        """与真实客户端的工厂方法对齐，编排层统一走这一条路径。"""
        return self(get_e2b_cluster_config(cluster_name))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def fail(self, method: str, exc: Exception):
        """让指定方法在下次调用时抛出异常。"""
        self.errors[method] = exc

    def create_sandbox(self, payload):
        self.created_payloads.append(payload)
        self._maybe_raise("create_sandbox")
        return dict(self.create_response)

    def get_sandbox(self, sandbox_id):
        self._maybe_raise("get_sandbox")
        return dict(self.get_response)

    def list_sandboxes(self):
        self._maybe_raise("list_sandboxes")
        return [dict(item) for item in self.list_response]

    def kill_sandbox(self, sandbox_id):
        self.killed.append(sandbox_id)
        self._maybe_raise("kill_sandbox")

    def set_timeout(self, sandbox_id, timeout):
        self.timeouts.append((sandbox_id, timeout))
        self._maybe_raise("set_timeout")

    def _maybe_raise(self, method: str):
        if exc := self.errors.get(method):
            raise exc


@pytest.fixture()
def gateway(monkeypatch, e2b_config) -> FakeGateway:
    fake = FakeGateway()
    monkeypatch.setattr(sandboxes, "E2BGatewayClient", fake)
    return fake


def _record(
    application, sandbox_id: str = SANDBOX_ID, cluster_name: str = CLUSTER_NAME_FOR_TESTING, **overrides
) -> E2BSandbox:
    return E2BSandbox.objects.create(
        sandbox_id=sandbox_id,
        application=application,
        cluster_name=cluster_name,
        tenant_id=DEFAULT_TENANT_ID,
        **overrides,
    )


class TestCreate:
    def test_records_ownership(self, gateway, bk_app):
        sandboxes.create_sandbox(bk_app, {"templateID": "e2b-envd"})

        record = E2BSandbox.objects.get(sandbox_id=SANDBOX_ID)
        assert record.application == bk_app
        assert record.cluster_name == CLUSTER_NAME_FOR_TESTING
        assert record.template_id == "e2b-envd"
        assert record.status == E2BSandboxStatus.RUNNING.value
        assert record.expired_at is not None

    def test_rewrites_data_plane_address(self, gateway, bk_app):
        """集群内域名换成对外地址，SDK 拿它拼数据面 URL。"""
        resp = sandboxes.create_sandbox(bk_app, {"templateID": "e2b-envd"})

        assert resp["domain"] == DATA_PLANE_ADDRESS

    def test_passes_through_other_fields(self, gateway, bk_app):
        """除地址字段外原样返回，包括访问令牌与我们不认识的新字段。"""
        gateway.create_response = _create_response(someFutureField="kept")

        resp = sandboxes.create_sandbox(bk_app, {"templateID": "e2b-envd"})

        assert resp["envdAccessToken"] == ACCESS_TOKEN
        assert resp["someFutureField"] == "kept"

    def test_forwards_request_body_verbatim(self, gateway, bk_app):
        """请求体整体转发，不因为服务层不认识某个参数就把它吃掉。"""
        payload = {"templateID": "e2b-envd", "timeout": 600, "metadata": {"owner": "a"}}

        sandboxes.create_sandbox(bk_app, payload)

        assert gateway.created_payloads == [payload]

    def test_rolls_back_when_recording_fails(self, gateway, bk_app):
        """落库失败同样要回滚。这里用重复的沙箱 ID 触发唯一约束冲突。"""
        _record(bk_app)

        with pytest.raises(IntegrityError):
            sandboxes.create_sandbox(bk_app, {"templateID": "e2b-envd"})

        assert gateway.killed == [SANDBOX_ID]

    def test_rollback_failure_does_not_mask_original_error(self, gateway, bk_app):
        """回滚自己也失败时，抛出的仍是根因，否则排查会被引向错误方向。"""
        _record(bk_app)
        gateway.fail("kill_sandbox", E2BGatewayUnavailable("gateway down"))

        with pytest.raises(IntegrityError):
            sandboxes.create_sandbox(bk_app, {"templateID": "e2b-envd"})


class TestGet:
    def test_rewrites_address_and_passes_token(self, gateway, bk_app):
        """令牌由网关每次重新签发，透传最新值而不是缓存。"""
        _record(bk_app)
        gateway.get_response = _create_response(envdAccessToken="refreshed-token")

        resp = sandboxes.get_sandbox(bk_app, SANDBOX_ID)

        assert resp["domain"] == DATA_PLANE_ADDRESS
        assert resp["envdAccessToken"] == "refreshed-token"

    def test_terminated_sandbox_is_invisible(self, gateway, bk_app):
        """销毁之后再查就该是 404，记录留着只是为了让重复销毁保持幂等。"""
        _record(bk_app, status=E2BSandboxStatus.TERMINATED.value)

        with pytest.raises(E2BSandboxNotFound):
            sandboxes.get_sandbox(bk_app, SANDBOX_ID)

    def test_gateway_404_becomes_not_found(self, gateway, bk_app):
        """本地有记录而网关侧已回收，对用户就是不存在。"""
        _record(bk_app)
        gateway.fail("get_sandbox", E2BGatewayNotFound("gone"))

        with pytest.raises(E2BSandboxNotFound):
            sandboxes.get_sandbox(bk_app, SANDBOX_ID)


class TestList:
    def test_returns_only_owned_sandboxes(self, gateway, bk_app, bk_app_full):
        """网关返回的是平台统一凭证下的全集，必须与本地归属表求交。"""
        _record(bk_app, "mine")
        _record(bk_app_full, "someone-else")
        gateway.list_response = [_create_response("mine"), _create_response("someone-else")]

        items = sandboxes.list_sandboxes(bk_app)

        assert [item["sandboxID"] for item in items] == ["mine"]

    def test_skips_terminated_records(self, gateway, bk_app):
        _record(bk_app, "alive")
        _record(bk_app, "dead", status=E2BSandboxStatus.TERMINATED.value)
        gateway.list_response = [_create_response("alive"), _create_response("dead")]

        items = sandboxes.list_sandboxes(bk_app)

        assert [item["sandboxID"] for item in items] == ["alive"]

    def test_skips_records_gateway_no_longer_has(self, gateway, bk_app):
        """本地记录还在但网关侧已回收的，不该出现在列表里。"""
        _record(bk_app, "alive")
        _record(bk_app, "reclaimed-by-gateway")
        gateway.list_response = [_create_response("alive")]

        items = sandboxes.list_sandboxes(bk_app)

        assert [item["sandboxID"] for item in items] == ["alive"]

    def test_unreachable_cluster_does_not_break_others(self, gateway, bk_app):
        """一个集群取不到，其余集群的结果照常返回。

        另一个集群用「未登记 e2b 配置」来模拟：取配置就会失败，
        与网关连不上走的是同一条跳过分支。
        """
        _record(bk_app, "on-healthy-cluster")
        _record(bk_app, "on-broken-cluster", cluster_name="cluster-never-registered")
        gateway.list_response = [_create_response("on-healthy-cluster")]

        items = sandboxes.list_sandboxes(bk_app)

        assert [item["sandboxID"] for item in items] == ["on-healthy-cluster"]

    def test_does_not_touch_gateway_when_nothing_owned(self, gateway, bk_app):
        assert sandboxes.list_sandboxes(bk_app) == []
        assert gateway.configs == []


class TestKill:
    def test_marks_terminated(self, gateway, bk_app):
        _record(bk_app)

        sandboxes.kill_sandbox(bk_app, SANDBOX_ID)

        assert gateway.killed == [SANDBOX_ID]
        assert E2BSandbox.objects.get(sandbox_id=SANDBOX_ID).status == E2BSandboxStatus.TERMINATED.value

    def test_repeated_kill_is_idempotent(self, gateway, bk_app):
        """已销毁的再销毁不报错，也不必再打一次网关。"""
        _record(bk_app)
        sandboxes.kill_sandbox(bk_app, SANDBOX_ID)

        sandboxes.kill_sandbox(bk_app, SANDBOX_ID)

        assert gateway.killed == [SANDBOX_ID]

    def test_gateway_404_is_treated_as_success(self, gateway, bk_app):
        """网关侧已经没有了，目标状态本就达成，本地跟着收敛即可。"""
        _record(bk_app)
        gateway.fail("kill_sandbox", E2BGatewayNotFound("gone"))

        sandboxes.kill_sandbox(bk_app, SANDBOX_ID)

        assert E2BSandbox.objects.get(sandbox_id=SANDBOX_ID).status == E2BSandboxStatus.TERMINATED.value

    def test_local_write_failure_does_not_fail_the_request(self, gateway, bk_app, monkeypatch):
        """网关已销毁成功，对用户而言操作完成了，不该因本地写失败而报错。"""
        _record(bk_app)

        def _boom(*args, **kwargs):
            raise RuntimeError("db is down")

        monkeypatch.setattr(E2BSandbox, "save", _boom)

        sandboxes.kill_sandbox(bk_app, SANDBOX_ID)

        assert gateway.killed == [SANDBOX_ID]


class TestSetTimeout:
    def test_forwards_to_owning_cluster(self, gateway, bk_app):
        _record(bk_app)

        sandboxes.set_sandbox_timeout(bk_app, SANDBOX_ID, 600)

        assert gateway.timeouts == [(SANDBOX_ID, 600)]
