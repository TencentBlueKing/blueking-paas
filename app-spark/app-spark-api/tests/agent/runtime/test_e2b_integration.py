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

"""Exercise the E2B provider and the real Agent Runtime its template ships."""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING
from uuid import uuid4

import attrs
import pytest
from e2b import NotFoundException

from app_spark_api.agent.runtime.client import AgentRuntimeClient
from app_spark_api.agent.runtime.exceptions import AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.e2b import STOP_GRACE_SECONDS, E2BProvider, _SandboxClaim
from tests.agent.runtime.e2b_support import FakeModelE2BProvider, logger, require_e2b_config

if TYPE_CHECKING:
    from e2b import AsyncSandbox

    from app_spark_api.agent.runtime.entities import E2BConfig

pytestmark = [pytest.mark.e2b, pytest.mark.django_db(transaction=True)]

# The sandbox is polled every 10 seconds, and E2B reaps an expired one on its own schedule.
IDLE_RECLAIM_SLACK_SECONDS = 30


async def check_sandbox_running(sandbox: AsyncSandbox) -> bool:
    """Ask envd whether a sandbox still runs; a control plane that forgot it answers 404."""
    try:
        return await sandbox.is_running()
    except NotFoundException:
        return False


@pytest.fixture
def e2b_config(settings) -> E2BConfig:
    """Use the configured E2B endpoint only when it is fully specified."""
    return require_e2b_config(settings)


@pytest.fixture
async def e2b_provider(e2b_config: E2BConfig):
    """Own and clean up every sandbox created by one test."""
    provider = FakeModelE2BProvider(e2b_config)
    try:
        yield provider
    finally:
        await provider.shutdown()


async def test_e2b_provider_creates_and_stops_sandbox(e2b_provider: E2BProvider):
    """Provider identity, command access, and cleanup all reach the live E2B API."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    next_conversation_id = str(uuid4())
    assert await e2b_provider.peek(conversation_id) is None
    assert await e2b_provider.get_sandbox(conversation_id) is None
    assert await e2b_provider.preview_target(conversation_id) is None
    await e2b_provider.terminate(conversation_id)

    logger.info("Creating sandbox for provider lifecycle test")
    handle = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert await e2b_provider.peek(conversation_id) == handle
    assert await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id) == handle
    with pytest.raises(AgentWorkspaceBusyError):
        await e2b_provider.ensure(project_id=project_id, conversation_id=next_conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)
    assert record.active_conversation_id == conversation_id
    assert (
        handle.base_url == f"{e2b_provider.config.port_scheme}://{sandbox.get_host(e2b_provider.config.runtime_port)}"
    )
    # Port-proxy credentials are whatever this sandbox actually issued.
    expected_headers: dict[str, str] = {}
    if access_token := sandbox.connection_config.sandbox_headers.get("X-Access-Token"):
        expected_headers["X-Access-Token"] = access_token
    if sandbox.traffic_access_token:
        expected_headers["E2B-Traffic-Access-Token"] = sandbox.traffic_access_token
    assert handle.http_headers == expected_headers
    target = await e2b_provider.preview_target(conversation_id)
    assert target is not None
    assert target.base_url == (
        f"{e2b_provider.config.port_scheme}://{sandbox.get_host(e2b_provider.config.preview_port)}"
    )
    assert target.http_headers == handle.http_headers
    assert target.send_forwarded_host is False
    result = await sandbox.commands.run("printf 'agent-sandbox-ready'", user=e2b_provider.config.agent_user)
    assert result.stdout == "agent-sandbox-ready"

    logger.info("Terminating sandbox %s and checking its retained record", sandbox.sandbox_id)
    await e2b_provider.terminate(conversation_id)
    await e2b_provider.terminate(conversation_id)
    assert await e2b_provider.peek(conversation_id) is None
    assert await e2b_provider.get_sandbox(conversation_id) is None
    assert await e2b_provider.preview_target(conversation_id) is None
    await record.arefresh_from_db()
    assert record.project_id == project_id
    assert record.conversation_id == conversation_id
    assert record.active_project_id is None
    assert record.active_conversation_id is None
    assert record.stopped_at is not None
    assert record.stop_reason == "terminated"

    logger.info("Reusing the released project for a new conversation")
    replacement = await e2b_provider.ensure(project_id=project_id, conversation_id=next_conversation_id)
    assert replacement.conversation_id == next_conversation_id
    assert await e2b_provider.peek(next_conversation_id) == replacement
    assert await E2BSandboxRecord.objects.active_for_project(project_id).acount() == 1


async def test_concurrent_ensures_of_one_conversation_share_one_sandbox(e2b_provider: E2BProvider):
    """Two requests on one worker wait, then share the sandbox, instead of one reporting busy.

    Creating a sandbox takes long enough that the two calls overlap. A missing per-conversation
    lock lets the second lose the claim and raise ``AgentWorkspaceBusyError``.
    """
    project_id = str(uuid4())
    conversation_id = str(uuid4())

    first, second = await asyncio.gather(
        e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id),
        e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id),
    )

    assert first == second
    assert await E2BSandboxRecord.objects.active_for_conversation(conversation_id).acount() == 1


async def test_e2b_sandbox_survives_provider_recreation(e2b_provider: E2BProvider):
    """A fresh provider reconnects from the database and can finish cleanup."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    original = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    record = await E2BSandboxRecord.objects.active_for_conversation(conversation_id).afirst()
    assert record is not None

    logger.info("Recreating provider and reconnecting to sandbox %s", record.sandbox_id)
    reloaded_provider = E2BProvider(e2b_provider.config)
    assert await reloaded_provider.peek(conversation_id) == original
    assert await reloaded_provider.ensure(project_id=project_id, conversation_id=conversation_id) == original
    assert await reloaded_provider.preview_target(conversation_id) is not None

    await reloaded_provider.shutdown()
    await reloaded_provider.shutdown()
    assert await e2b_provider.peek(conversation_id) is None
    await record.arefresh_from_db()
    assert record.stop_reason == "terminated"


async def test_e2b_provider_releases_expired_sandbox(e2b_provider: E2BProvider):
    """A sandbox removed outside the provider frees its project and leaves a history row.

    Looking does not release it; the next ensure does, and replaces it.
    """
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None

    logger.info("Killing sandbox %s externally to verify expiry detection", sandbox.sandbox_id)
    await sandbox.kill()
    assert await e2b_provider.peek(conversation_id) is None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)
    assert record.active_conversation_id == conversation_id

    replacement = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    await record.arefresh_from_db()
    assert record.active_project_id is None
    assert record.active_conversation_id is None
    assert record.stopped_at is not None
    assert record.stop_reason == "expired"
    assert await e2b_provider.peek(conversation_id) == replacement


async def test_the_provider_starts_an_agent_that_runs_a_real_fake_turn(e2b_provider: E2BProvider):
    """The provider's own start reaches the Agent's HTTP port, and its fake model writes a file."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    logger.info("Creating sandbox and starting a real Agent for a fake chat turn")
    handle = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)
    assert record.agent_pid is not None

    # ensure returns only once /health answered, so no waiting is needed here.
    client = AgentRuntimeClient(handle)
    health = await client.health()
    assert health.model == "fake:write-file"
    assert health.conversation_id is None

    logger.info("Submitting fake Agent turn through the exposed E2B port")
    run = await client.start_run(content="write my first note", context_version=health.context_version)
    event_stream = b"".join([part async for part in run.aiter_bytes()])
    assert b"RUN_FINISHED" in event_stream
    note = f"{e2b_provider.config.workspace_dir}/fake-agent-note-1.md"
    # As the Agent's user, the same way the provider itself reaches into the sandbox.
    assert "write my first note" in await sandbox.files.read(note, user=e2b_provider.config.agent_user)
    logger.info("Fake Agent turn completed and workspace note was verified")


async def test_a_stopped_agent_exits_on_sigterm_within_the_grace_period(e2b_provider: E2BProvider):
    """The stop command signals the real Agent process from inside the sandbox and waits for it."""
    conversation_id = str(uuid4())
    await e2b_provider.ensure(project_id=str(uuid4()), conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)

    started = time.monotonic()
    await _SandboxClaim(record, e2b_provider.config).stop_agent(sandbox, grace_seconds=STOP_GRACE_SECONDS)

    assert time.monotonic() - started < STOP_GRACE_SECONDS
    gone = await sandbox.commands.run(
        f"kill -0 {record.agent_pid} 2>/dev/null && echo alive || echo gone", user=e2b_provider.config.agent_user
    )
    assert gone.stdout.strip() == "gone"


async def test_a_crashed_agent_is_replaced_by_a_new_sandbox(e2b_provider: E2BProvider):
    """沙箱还在、Agent 没了：下一轮不在原沙箱里重拉，而是整个换掉。"""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    original = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)
    assert record.agent_pid is not None

    logger.info("Killing the Agent in sandbox %s, leaving the sandbox itself up", sandbox.sandbox_id)
    await sandbox.commands.kill(record.agent_pid)
    replacement = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert replacement != original
    await record.arefresh_from_db()
    assert (record.active_conversation_id, record.stop_reason) == (None, "unhealthy")
    assert not await check_sandbox_running(sandbox)


@pytest.mark.skipif(
    os.environ.get("APP_SPARK_E2B_IDLE_LIVE") != "1",
    reason="waits three minutes for a real idle reclamation; set APP_SPARK_E2B_IDLE_LIVE=1",
)
async def test_an_idle_sandbox_is_reclaimed_when_its_idle_timeout_elapses(
    e2b_config: E2BConfig, agent_bundle: AgentBundle
):
    """空闲超时设为 120 秒时，一轮结束后沙箱在这个秒数左右被回收。"""
    idle_timeout = 120
    provider = FakeModelE2BProvider(attrs.evolve(e2b_config, idle_timeout_seconds=idle_timeout))
    conversation_id = str(uuid4())
    try:
        await provider.ensure(project_id=str(uuid4()), conversation_id=conversation_id)
        sandbox = await provider.get_sandbox(conversation_id)
        assert sandbox is not None

        # The Agent never ran a turn, so its idle timer started with its process, just before this;
        # the renewal is the one a turn's end makes, and the sandbox deadline is that same interval.
        await provider.extend_lifetime(conversation_id)
        turn_ended = time.monotonic()

        while await check_sandbox_running(sandbox):
            elapsed = time.monotonic() - turn_ended
            assert elapsed < idle_timeout + IDLE_RECLAIM_SLACK_SECONDS, "the idle sandbox outlived its idle timeout"
            await asyncio.sleep(10)

        # Gone before the Agent could idle out would mean it was not given the chance to push.
        assert time.monotonic() - turn_ended > idle_timeout - IDLE_RECLAIM_SLACK_SECONDS, (
            "the sandbox was reclaimed before its Agent's idle timeout"
        )
    finally:
        await provider.shutdown()
