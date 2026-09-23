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

"""Exercise the E2B provider and a real Agent Runtime in a default sandbox."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app_spark_api.agent.runtime.client import AgentRuntimeClient
from app_spark_api.agent.runtime.exceptions import AgentWorkspaceBusyError
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers.e2b import E2BProvider
from tests.agent.runtime.e2b_support import (
    SANDBOX_WORKSPACE,
    AgentBundle,
    build_agent_bundle,
    install_agent_bundle,
    logger,
    require_e2b_config,
    start_agent,
    wait_for_health,
)

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.entities import E2BConfig

pytestmark = [pytest.mark.e2b, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def e2b_config(settings) -> E2BConfig:
    """Use the configured E2B endpoint only when it is fully specified."""
    return require_e2b_config(settings)


@pytest.fixture
async def e2b_provider(e2b_config: E2BConfig):
    """Own and clean up every sandbox created by one test."""
    provider = E2BProvider(e2b_config)
    try:
        yield provider
    finally:
        await provider.shutdown()


@pytest.fixture
def agent_bundle(tmp_path, e2b_config: E2BConfig) -> AgentBundle:
    """Prepare local artifacts after the E2B skip condition has been checked."""
    return build_agent_bundle(tmp_path)


async def test_e2b_provider_creates_and_stops_sandbox(e2b_provider: E2BProvider):
    """Provider identity, command access, and cleanup all reach the live E2B API."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    next_conversation_id = str(uuid4())
    assert await e2b_provider.peek(conversation_id) is None
    assert await e2b_provider.get_sandbox(conversation_id) is None
    assert await e2b_provider.preview_upstream(conversation_id) is None
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
    assert await e2b_provider.preview_upstream(conversation_id) == (
        f"{e2b_provider.config.port_scheme}://{sandbox.get_host(e2b_provider.config.preview_port)}"
    )
    result = await sandbox.commands.run("printf 'agent-sandbox-ready'")
    assert result.stdout == "agent-sandbox-ready"

    logger.info("Terminating sandbox %s and checking its retained record", sandbox.sandbox_id)
    await e2b_provider.terminate(conversation_id)
    await e2b_provider.terminate(conversation_id)
    assert await e2b_provider.peek(conversation_id) is None
    assert await e2b_provider.get_sandbox(conversation_id) is None
    assert await e2b_provider.preview_upstream(conversation_id) is None
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
    assert await reloaded_provider.preview_upstream(conversation_id) is not None

    await reloaded_provider.shutdown()
    await reloaded_provider.shutdown()
    assert await e2b_provider.peek(conversation_id) is None
    await record.arefresh_from_db()
    assert record.stop_reason == "terminated"


async def test_e2b_provider_releases_expired_sandbox(e2b_provider: E2BProvider):
    """A sandbox removed outside the provider frees its project and leaves a history row."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None

    logger.info("Killing sandbox %s externally to verify expiry detection", sandbox.sandbox_id)
    await sandbox.kill()
    assert await e2b_provider.peek(conversation_id) is None
    record = await E2BSandboxRecord.objects.aget(sandbox_id=sandbox.sandbox_id)
    assert record.active_project_id is None
    assert record.active_conversation_id is None
    assert record.stopped_at is not None
    assert record.stop_reason == "expired"


async def test_agent_wheel_runs_a_real_fake_turn_in_e2b(e2b_provider: E2BProvider, agent_bundle: AgentBundle):
    """Install the wheel, reach its HTTP port, and make its fake model write a file."""
    project_id = str(uuid4())
    conversation_id = str(uuid4())
    logger.info("Creating sandbox and installing real Agent for fake chat turn")
    handle = await e2b_provider.ensure(project_id=project_id, conversation_id=conversation_id)
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None

    await install_agent_bundle(sandbox, agent_bundle)
    await start_agent(
        sandbox,
        handle,
        port=e2b_provider.config.runtime_port,
        app_port=e2b_provider.config.preview_port,
        project_id=project_id,
    )

    client = AgentRuntimeClient(handle)
    health = await wait_for_health(sandbox, client, port=e2b_provider.config.runtime_port)
    assert health.model == "fake:write-file"
    assert health.conversation_id is None

    logger.info("Submitting fake Agent turn through the exposed E2B port")
    run = await client.start_run(content="write my first note", context_version=health.context_version)
    event_stream = b"".join([part async for part in run.aiter_bytes()])
    assert b"RUN_FINISHED" in event_stream
    assert "write my first note" in await sandbox.files.read(f"{SANDBOX_WORKSPACE}/fake-agent-note-1.md")
    logger.info("Fake Agent turn completed and workspace note was verified")
