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

"""Install a real Agent into E2B while exercising the API's normal provider path."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from app_spark_api.agent.runtime import AgentRuntimeClient
from app_spark_api.agent.runtime import factory as runtime_factory
from app_spark_api.agent.runtime.providers.e2b import E2BProvider
from app_spark_api.repository.git.services import provision_project_repository
from tests.agent.runtime.e2b_support import (
    AgentBundle,
    build_agent_bundle,
    install_agent_bundle,
    logger,
    require_e2b_config,
    start_agent,
    wait_for_health,
)
from tests.api.support import create_reachable_project

if TYPE_CHECKING:
    from collections.abc import Callable

    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, E2BConfig, GitRemote, StateCallback


class BootstrappedE2BProvider(E2BProvider):
    """Make the default template usable for live API tests after provisioning."""

    def __init__(self, config: E2BConfig, bundle: AgentBundle) -> None:
        super().__init__(config)
        self.bundle = bundle
        self._bootstrapped: set[str] = set()
        self._bootstrap_lock = asyncio.Lock()

    async def ensure(
        self,
        *,
        project_id: str,
        conversation_id: str,
        state_callback: StateCallback | None = None,
        git_remote: GitRemote | None = None,
    ) -> AgentRuntimeHandle:
        """Provision through the real provider, then install the test Agent once.

        :param project_id: Project being served.
        :param conversation_id: Conversation being served.
        :param state_callback: Callback passed through to the production provider.
        :param git_remote: Repository details passed through to the production provider.
        :return: Handle of the healthy Agent Runtime.
        """
        handle = await super().ensure(
            project_id=project_id,
            conversation_id=conversation_id,
            state_callback=state_callback,
            git_remote=git_remote,
        )
        async with self._bootstrap_lock:
            if conversation_id not in self._bootstrapped:
                sandbox = await self.get_sandbox(conversation_id)
                assert sandbox is not None
                logger.info("Bootstrapping API conversation %s in sandbox %s", conversation_id, sandbox.sandbox_id)
                await install_agent_bundle(sandbox, self.bundle)
                await start_agent(
                    sandbox,
                    handle,
                    port=self.config.runtime_port,
                    app_port=self.config.preview_port,
                    project_id=project_id,
                )
                await wait_for_health(sandbox, AgentRuntimeClient(handle), port=self.config.runtime_port)
                self._bootstrapped.add(conversation_id)
        return handle


@pytest.fixture
def e2b_config(settings) -> E2BConfig:
    """Skip live API tests unless the service has a valid E2B configuration."""
    return require_e2b_config(settings)


@pytest.fixture(scope="session")
def agent_bundle_factory(tmp_path_factory) -> Callable[[], AgentBundle]:
    """Build once, and only after a test has passed the E2B configuration gate."""
    bundle: AgentBundle | None = None

    def get_bundle() -> AgentBundle:
        nonlocal bundle
        if bundle is None:
            bundle = build_agent_bundle(tmp_path_factory.mktemp("live-e2b-agent"))
        return bundle

    return get_bundle


@pytest.fixture
def agent_bundle(e2b_config: E2BConfig, agent_bundle_factory: Callable[[], AgentBundle]) -> AgentBundle:
    """Get the wheel bundle after the E2B skip condition has been checked."""
    return agent_bundle_factory()


@pytest.fixture
def project(bk_user, fake_forgejo):
    """Give the API a project with a provisioned (fake) repository."""
    project = create_reachable_project(bk_user)
    provision_project_repository(project)
    return project


@pytest.fixture
async def e2b_provider(monkeypatch, e2b_config: E2BConfig, agent_bundle: AgentBundle):
    """Run the API against a provider that test-installs the Agent and cleans up."""
    provider = BootstrappedE2BProvider(e2b_config, agent_bundle)
    monkeypatch.setattr(runtime_factory, "_provider", provider)
    try:
        yield provider
    finally:
        logger.info("Cleaning up live API E2B sandboxes")
        await provider.shutdown()
