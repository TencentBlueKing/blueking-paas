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

"""Races and injected failures the live E2B suite cannot stage.

``test_e2b_integration.py`` already drives a real sandbox through create, reuse, preview,
busy projects, shutdown, and expiry. What it cannot do on demand is fail at a chosen moment,
move the clock past an abandoned claim, or hold one create open while another request runs.
A second provider instance stands in for another API worker: it shares nothing with the first
but the database, exactly like a worker in another process.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from django.utils import timezone
from e2b import AsyncSandbox, NotFoundException, SandboxException

from app_spark_api.agent.runtime.entities import E2BConfig
from app_spark_api.agent.runtime.exceptions import AgentProvisionError, AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.e2b import ABANDONED_CLAIM_SECONDS, E2BProvider, _SandboxClaim

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

pytestmark = pytest.mark.django_db(transaction=True)

CONFIG = E2BConfig(api_key="e2b-key", api_url="https://e2b.example", domain="sandbox.example")


class FakeSandbox:
    """The part of ``AsyncSandbox`` the provider touches, with switches to make it fail."""

    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        self.sandbox_domain = "sandbox.example"
        self.traffic_access_token = f"traffic-{sandbox_id}"
        self.connection_config = SimpleNamespace(sandbox_headers={"X-Access-Token": f"envd-{sandbox_id}"})
        self.killed = False
        self.info_error: Exception | None = None
        self.kill_error: Exception | None = None

    async def get_info(self) -> SimpleNamespace:
        if self.info_error is not None:
            raise self.info_error
        return SimpleNamespace(sandbox_domain=self.sandbox_domain, envd_version="0.2.0")

    async def is_running(self) -> bool:
        return not self.killed

    async def kill(self) -> None:
        if self.kill_error is not None:
            raise self.kill_error
        self.killed = True

    def get_host(self, port: int) -> str:
        return f"{port}-{self.sandbox_id}.{self.sandbox_domain}"


class FakeE2B:
    """Stands in for the control plane behind ``AsyncSandbox.create`` and ``connect``."""

    def __init__(self) -> None:
        self.sandboxes: dict[str, FakeSandbox] = {}
        self.create_calls = 0
        self.connect_calls = 0
        self.create_started = asyncio.Event()
        self.create_error: Exception | None = None
        self.connect_error: Exception | None = None
        # Runs inside `create` before it answers, which is where a race or a failure is staged.
        self.on_create: Callable[[int], Awaitable[None]] | None = None
        # Applied to each sandbox before it is handed back, to stage a failure after creation.
        self.prepare: Callable[[FakeSandbox], None] | None = None

    async def create(self, template: str, **_opts: object) -> FakeSandbox:
        self.create_calls += 1
        self.create_started.set()
        call = self.create_calls
        if self.on_create is not None:
            await self.on_create(call)
        if self.create_error is not None:
            raise self.create_error
        sandbox = FakeSandbox(f"sbx-{call}")
        if self.prepare is not None:
            self.prepare(sandbox)
        self.sandboxes[sandbox.sandbox_id] = sandbox
        return sandbox

    async def connect(self, sandbox_id: str, **_opts: object) -> FakeSandbox:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        try:
            return self.sandboxes[sandbox_id]
        except KeyError:
            raise NotFoundException(sandbox_id) from None


@pytest.fixture
def e2b(monkeypatch) -> FakeE2B:
    fake = FakeE2B()
    monkeypatch.setattr(AsyncSandbox, "create", staticmethod(fake.create))
    monkeypatch.setattr(AsyncSandbox, "connect", staticmethod(fake.connect))
    return fake


@pytest.fixture
def provider() -> E2BProvider:
    return E2BProvider(CONFIG)


@pytest.fixture
def other_worker() -> E2BProvider:
    """A provider that shares only the database with ``provider``, like a second API worker."""
    return E2BProvider(CONFIG)


def ids() -> tuple[str, str]:
    return str(uuid4()), str(uuid4())


async def create_started(e2b: FakeE2B) -> None:
    """Wait until another task has claimed and reached E2B; the claim goes through a DB thread."""
    await asyncio.wait_for(e2b.create_started.wait(), timeout=5)


# --- 先占位，再建沙箱 ----------------------------------------------------------------------


async def test_conversations_do_not_wait_behind_each_other(e2b, provider):
    """锁按会话分：一个会话卡在建沙箱上，别的会话照常。"""
    released = asyncio.Event()

    async def stall_first(call: int) -> None:
        if call == 1:
            await released.wait()

    e2b.on_create = stall_first
    stalled = asyncio.create_task(provider.ensure(project_id=str(uuid4()), conversation_id=str(uuid4())))
    try:
        await create_started(e2b)

        await asyncio.wait_for(provider.ensure(project_id=str(uuid4()), conversation_id=str(uuid4())), timeout=5)
    finally:
        released.set()
        await stalled


async def test_two_workers_racing_for_one_conversation_create_one_sandbox(e2b, provider, other_worker):
    """两个 worker 谁先占到位谁建，输的那个一个沙箱都没建过，也就没有要回收的东西。"""
    project_id, conversation_id = ids()

    async def slow_create(_call: int) -> None:
        await asyncio.sleep(0.05)

    e2b.on_create = slow_create
    outcomes = await asyncio.gather(
        provider.ensure(project_id=project_id, conversation_id=conversation_id),
        other_worker.ensure(project_id=project_id, conversation_id=conversation_id),
        return_exceptions=True,
    )

    assert sorted(type(outcome).__name__ for outcome in outcomes) == ["AgentRuntimeHandle", "AgentWorkspaceBusyError"]
    assert e2b.create_calls == 1
    assert not any(sandbox.killed for sandbox in e2b.sandboxes.values())


async def test_a_claim_in_progress_is_busy_until_it_is_old_enough_to_be_abandoned(e2b, provider):
    """另一个 worker 正在建的占位要等；它死在半路留下的占位不能永远占着 Project。"""
    project_id, conversation_id = ids()
    orphan = await E2BSandboxRecord.objects.acreate(
        project_id=project_id,
        conversation_id="elsewhere",
        active_project_id=project_id,
        active_conversation_id="elsewhere",
        runtime_token="token",
        template=CONFIG.template,
    )

    with pytest.raises(AgentWorkspaceBusyError):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    assert e2b.create_calls == 0

    await E2BSandboxRecord.objects.filter(pk=orphan.pk).aupdate(
        created_at=timezone.now() - timedelta(seconds=ABANDONED_CLAIM_SECONDS + 1)
    )
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    await orphan.arefresh_from_db()
    assert (orphan.active_project_id, orphan.stop_reason) == (None, "abandoned")


async def test_a_stale_abandoned_view_does_not_release_a_sandbox_bound_since(e2b, provider):
    """读到「还没绑定」之后沙箱已经绑上了，不能按 abandoned 把活记录放掉。"""
    project_id, conversation_id = ids()
    stale: dict[str, E2BSandboxRecord] = {}

    async def remember_the_unbound_claim(_call: int) -> None:
        stale["record"] = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)

    e2b.on_create = remember_the_unbound_claim
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    # The in-memory row is what a concurrent ensure loaded before the bind landed, and it is
    # old enough that the abandoned check would otherwise give the claim away.
    stale["record"].created_at = timezone.now() - timedelta(seconds=ABANDONED_CLAIM_SECONDS + 1)

    assert await _SandboxClaim(stale["record"], provider.config).connect(reconcile=True) is not None

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (conversation_id, "sbx-1", "")
    assert not e2b.sandboxes["sbx-1"].killed


# --- 失败时交还占位 --------------------------------------------------------------------------


async def test_a_failed_create_gives_its_claim_back(e2b, provider):
    project_id, conversation_id = ids()
    e2b.create_error = SandboxException("quota exceeded")

    with pytest.raises(AgentProvisionError, match="quota exceeded"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, None, "failed")

    e2b.create_error = None
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)


async def test_a_cleanup_failure_does_not_replace_the_provisioning_error(e2b, provider):
    """清理是尽力而为：kill 失败只记日志，调用方看到的仍是原本那个错，占位也照样交还。"""
    project_id, conversation_id = ids()

    def break_after_creation(sandbox: FakeSandbox) -> None:
        sandbox.info_error = SandboxException("envd unreachable")
        sandbox.kill_error = SandboxException("kill refused")

    e2b.prepare = break_after_creation

    with pytest.raises(AgentProvisionError, match="envd unreachable"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert not await E2BSandboxRecord.objects.active_for_project(project_id).aexists()


async def test_a_claim_released_during_creation_takes_the_new_sandbox_down(e2b, provider, other_worker):
    """建沙箱那几秒里，另一个 worker 结束了这个会话。新沙箱不能挂在一条已经释放的记录上。"""
    project_id, conversation_id = ids()

    async def terminate_meanwhile(_call: int) -> None:
        await other_worker.terminate(conversation_id)

    e2b.on_create = terminate_meanwhile

    with pytest.raises(AgentProvisionError, match="released"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, None, "terminated")


async def test_terminating_a_claim_bound_since_it_was_read_still_kills_the_sandbox(e2b, provider, other_worker):
    """terminate 读到未绑定的占位时，绑定可能已经落库。放掉记录的同时必须把那个沙箱杀掉。"""
    project_id, conversation_id = ids()
    stale: dict[str, E2BSandboxRecord] = {}

    async def remember_the_unbound_claim(_call: int) -> None:
        stale["record"] = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)

    e2b.on_create = remember_the_unbound_claim
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    assert stale["record"].sandbox_id is None

    await _SandboxClaim(stale["record"], other_worker.config).terminate()

    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, "sbx-1", "terminated")


async def test_a_cancelled_provisioning_gives_its_claim_back(e2b, provider):
    """请求被断开时 ensure 被取消，占位不能留到被当成 abandoned 才放出来。"""
    project_id, conversation_id = ids()
    never = asyncio.Event()

    async def hang(_call: int) -> None:
        await never.wait()

    e2b.on_create = hang
    task = asyncio.create_task(provider.ensure(project_id=project_id, conversation_id=conversation_id))
    await create_started(e2b)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.stop_reason) == (None, "failed")


# --- 看一眼没有副作用 ------------------------------------------------------------------------


async def test_a_control_plane_hiccup_while_looking_does_not_release_the_sandbox(e2b, provider):
    """状态轮询时控制面抛错，不能把一条还占着的记录放掉。"""
    project_id, conversation_id = ids()
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    e2b.connect_error = SandboxException("control plane hiccup")

    with pytest.raises(AgentProvisionError, match="control plane hiccup"):
        await provider.peek(conversation_id)

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.stop_reason) == (conversation_id, "")


async def test_the_preview_target_does_not_ask_e2b(e2b, provider):
    """预览页的每个静态资源都会走这里。集成测试对得上真实地址，这里只证明这一步不再请求 E2B。"""
    project_id, conversation_id = ids()
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    e2b.connect_calls = 0

    target = await provider.preview_target(conversation_id)

    assert target is not None
    assert target.http_headers == {
        "X-Access-Token": "envd-sbx-1",
        "E2B-Traffic-Access-Token": "traffic-sbx-1",
    }
    assert e2b.connect_calls == 0


async def test_an_unbound_claim_has_nothing_to_preview_or_peek_at(e2b, provider):
    project_id, conversation_id = ids()
    await E2BSandboxRecord.objects.acreate(
        project_id=project_id,
        conversation_id=conversation_id,
        active_project_id=project_id,
        active_conversation_id=conversation_id,
        runtime_token="token",
        template=CONFIG.template,
    )

    assert await provider.preview_target(conversation_id) is None
    assert await provider.peek(conversation_id) is None
    assert e2b.connect_calls == 0
