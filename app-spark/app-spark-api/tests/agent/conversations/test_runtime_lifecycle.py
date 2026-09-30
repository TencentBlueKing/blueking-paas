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

"""What the conversation service tells the provider about a Runtime's use, and reads back.

Only turns count as activity, so the end of every turn renews the Runtime; looking at a
conversation must neither renew nor rebuild one, and has to say truthfully when there is none.
"""

import asyncio
from typing import TYPE_CHECKING, Any

import attrs
import pytest

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.runtime import AgentRuntimeHandle, AgentUnavailableError, RuntimeHealth
from app_spark_api.core.projects.models import Project

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

pytestmark = pytest.mark.django_db

HANDLE = AgentRuntimeHandle(conversation_id="c", base_url="http://127.0.0.1:1", runtime_token="t")
HEALTH = RuntimeHealth(
    model="fake:write-file",
    conversation_id=None,
    context_version=0,
    log_seq=0,
    ui_event_seq=0,
    running=True,
    dev_server_status="ready",
)


class FakeProvider:
    """A provider that starts nothing and records how it was used."""

    def __init__(self) -> None:
        self.handle: AgentRuntimeHandle | None = HANDLE
        self.replacing = False
        self.extended: list[str] = []
        self.extend_error: Exception | None = None

    async def peek(self, conversation_id: str) -> AgentRuntimeHandle | None:
        return self.handle

    async def needs_replacement(self, conversation_id: str) -> bool:
        return self.replacing

    async def extend_lifetime(self, conversation_id: str) -> None:
        if self.extend_error is not None:
            raise self.extend_error
        self.extended.append(conversation_id)


class FakeClient:
    """Stands in for AgentRuntimeClient; the class attributes decide how /health answers."""

    health_error: Exception | None = None
    answer: RuntimeHealth = HEALTH

    def __init__(self, handle: AgentRuntimeHandle, **_kwargs: Any) -> None:
        self.handle = handle

    async def health(self) -> RuntimeHealth:
        if self.health_error is not None:
            raise self.health_error
        return self.answer


class FakeRun:
    """The part of AgentRun that stream_run touches."""

    run_id = "run-1"

    def __init__(self, chunks: list[bytes], error: Exception | None = None, pause: float = 0) -> None:
        self.chunks = chunks
        self.error = error
        # How long the Agent stays silent before each chunk, like a long tool call.
        self.pause = pause

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            await asyncio.sleep(self.pause)
            yield chunk
        if self.error is not None:
            raise self.error


@pytest.fixture
def provider(monkeypatch) -> FakeProvider:
    fake = FakeProvider()
    monkeypatch.setattr(services, "get_agent_runtime_provider", lambda: fake)
    monkeypatch.setattr(services, "AgentRuntimeClient", FakeClient)
    monkeypatch.setattr(FakeClient, "health_error", None)
    monkeypatch.setattr(FakeClient, "answer", HEALTH)
    return fake


@pytest.fixture
def conversation(bk_user) -> Conversation:
    project = Project.objects.create(
        id="runtime-lifecycle",
        name="Runtime Lifecycle",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


async def collect_stream(run: FakeRun, conversation: Conversation) -> list[bytes]:
    return [chunk async for chunk in services.stream_run(run, conversation.id)]  # type: ignore[arg-type]


# --- 状态查询 --------------------------------------------------------------------------------


async def test_a_healthy_runtime_is_ready_for_the_next_turn(provider, conversation):
    state = await services.get_state(conversation)

    assert (state.runtime_ready, state.running, state.dev_server_status) == (True, True, "ready")


async def test_no_runtime_means_the_next_turn_prepares_one(provider, conversation):
    provider.handle = None

    state = await services.get_state(conversation)

    assert (state.runtime_ready, state.running, state.model) == (False, False, None)


async def test_an_agent_that_does_not_answer_is_reported_as_no_runtime(provider, conversation):
    """Agent 已退出、沙箱还在：前端轮询时如实报「无可用运行环境」，不报错、不续期、不重建。"""
    FakeClient.health_error = AgentUnavailableError("connection refused")

    state = await services.get_state(conversation)

    assert (state.runtime_ready, state.running, state.dev_server_status) == (False, False, None)
    assert provider.extended == []


async def test_a_runtime_about_to_be_replaced_is_not_ready(provider, conversation):
    """到了最长存活期的沙箱下一轮会被重建，前端要照样提示「正在准备运行环境」。"""
    provider.replacing = True
    FakeClient.answer = attrs.evolve(HEALTH, running=False)

    state = await services.get_state(conversation)

    assert state.runtime_ready is False
    # Still the live Runtime's own facts: it serves previews until the next turn replaces it.
    assert state.dev_server_status == "ready"


async def test_a_runtime_past_its_lifetime_mid_turn_is_not_replaced_so_it_is_ready(provider, conversation):
    """有一轮在跑时 ensure 不会换掉它，不能让前端误报「正在准备运行环境」。"""
    provider.replacing = True

    state = await services.get_state(conversation)

    assert (state.running, state.runtime_ready) == (True, True)


# --- 一轮结束时续期 ----------------------------------------------------------------------------


async def test_the_end_of_a_turn_renews_its_runtime(provider, conversation):
    chunks = await collect_stream(FakeRun([b"data: {}\n\n"]), conversation)

    assert chunks == [b"data: {}\n\n"]
    assert provider.extended == [str(conversation.id)]


async def test_a_long_turn_keeps_renewing_its_runtime_while_it_runs(provider, conversation, monkeypatch):
    """跑得比空闲超时还长的一轮，中途要一直续，哪怕 Agent 很久不吐一个字节。"""
    monkeypatch.setattr(services, "RUN_RENEWAL_INTERVAL_SECONDS", 0.01)

    await collect_stream(FakeRun([b"data: {}\n\n"], pause=0.1), conversation)

    # Several renewals while the Agent stayed silent, plus the one at the end of the turn.
    assert len(provider.extended) >= 3
    ended_with = len(provider.extended)
    await asyncio.sleep(0.05)
    assert len(provider.extended) == ended_with, "renewals must stop once the turn has ended"


async def test_a_turn_that_broke_mid_stream_still_renews_its_runtime(provider, conversation):
    chunks = await collect_stream(FakeRun([b"data: {}\n\n"], error=RuntimeError("reset")), conversation)

    assert b"RUN_ERROR" in chunks[-1]
    assert provider.extended == [str(conversation.id)]


async def test_a_failed_renewal_does_not_break_the_finished_turn(provider, conversation, caplog):
    provider.extend_error = RuntimeError("database gone")

    chunks = await collect_stream(FakeRun([b"data: {}\n\n"]), conversation)

    assert chunks == [b"data: {}\n\n"]
    assert any("Could not extend" in r.message for r in caplog.records if r.levelname == "WARNING")
