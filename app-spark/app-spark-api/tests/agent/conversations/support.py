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

"""Stand-ins for the provider and the Runtime client, shared by the conversation service tests.

Plain names rather than fixtures, for the reason ``tests/api/support.py`` gives: each test file
wraps what it needs in a fixture of its own, so nothing is taken over by fixture overriding.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app_spark_api.agent.conversations import services
from app_spark_api.agent.runtime import AgentRuntimeHandle, RuntimeHealth

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import pytest

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
    # What POST /runs/{id}/stop answers, and the run ids it was asked to stop.
    stop_accepted: bool = True
    stopped: list[str] = []

    def __init__(self, handle: AgentRuntimeHandle, **_kwargs: Any) -> None:
        self.handle = handle

    async def health(self) -> RuntimeHealth:
        if self.health_error is not None:
            raise self.health_error
        return self.answer

    async def stop_run(self, run_id: str) -> bool:
        self.stopped.append(run_id)
        return self.stop_accepted


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


def install_fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    """Point the conversation service at a fresh FakeProvider and at FakeClient, reset to a healthy Runtime."""
    fake = FakeProvider()
    monkeypatch.setattr(services, "get_agent_runtime_provider", lambda: fake)
    monkeypatch.setattr(services, "AgentRuntimeClient", FakeClient)
    monkeypatch.setattr(FakeClient, "health_error", None)
    monkeypatch.setattr(FakeClient, "answer", HEALTH)
    monkeypatch.setattr(FakeClient, "stop_accepted", True)
    monkeypatch.setattr(FakeClient, "stopped", [])
    return fake
