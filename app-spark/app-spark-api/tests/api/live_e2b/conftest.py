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

from typing import TYPE_CHECKING

import pytest

from app_spark_api.agent.runtime import factory as runtime_factory
from app_spark_api.repository.git.services import provision_project_repository
from tests.agent.runtime.e2b_support import (
    AgentBundle,
    BootstrappedE2BProvider,
    build_agent_bundle,
    logger,
    require_e2b_config,
)
from tests.api.support import create_reachable_project

if TYPE_CHECKING:
    from collections.abc import Callable

    from app_spark_api.agent.runtime.entities import E2BConfig


@pytest.fixture
def e2b_config(settings) -> E2BConfig:
    """Skip live API tests unless the service has a valid E2B configuration.

    The API resolves model access itself before the provider starts an Agent; the default bkaidev
    source would need a token exchange these tests have no user for.
    """
    config = require_e2b_config(settings)
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "fake:write-file"}
    return config


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
