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

"""Point the live E2B suites at the configured Agent template.

The template is built from app-spark/agent/Dockerfile and already ships the Agent, so the live
tests start it exactly the way production does, with nothing installed into the sandbox first.
Without a configured template they skip.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import attrs
import pytest

from app_spark_api.agent.runtime.entities import DirectModelAccess, E2BConfig, structure_e2b_config
from app_spark_api.agent.runtime.exceptions import AgentConfigurationError
from app_spark_api.agent.runtime.providers.e2b import E2BProvider

if TYPE_CHECKING:
    from app_spark_api.agent.runtime.entities import AgentRuntimeHandle, ModelAccess

LIVE_E2B_TIMEOUT_SECONDS = 300

# The live suites do not verify replication out of the sandbox, which cannot reach a test server
# on this machine anyway. A callback address configured in the settings still wins.
UNREACHABLE_CALLBACK_BASE_URL = "http://127.0.0.1:9"

logger = logging.getLogger("tests.e2b")


def require_e2b_config(settings: Any) -> E2BConfig:
    """Skip a live test unless the API service has a usable E2B configuration.

    :param settings: Django settings object supplied by pytest-django.
    :return: Valid E2B connection settings with a short test sandbox lifetime.
    """
    if settings.AGENT_RUNTIME_PROVIDER != "e2b":
        pytest.skip("AGENT_RUNTIME_PROVIDER is not e2b")
    # Checked apart from the rest, so the skip says which setting is missing: there is no
    # default template to fall back on.
    if not settings.AGENT_RUNTIME_PROVIDER_CONFIG.get("template"):
        pytest.skip("AGENT_RUNTIME_PROVIDER_CONFIG.template is not configured")
    raw_config = {"callback_base_url": UNREACHABLE_CALLBACK_BASE_URL, **settings.AGENT_RUNTIME_PROVIDER_CONFIG}
    try:
        config = structure_e2b_config(raw_config)
    except AgentConfigurationError:
        pytest.skip("A valid E2B provider configuration is required")
    # Fixtures normally kill their sandboxes; this bounds leaked resources if a test worker
    # dies. A test lasts a few minutes, and every turn renews it, so nothing idles out mid-test.
    return attrs.evolve(config, idle_timeout_seconds=LIVE_E2B_TIMEOUT_SECONDS)


async def resolve_fake_model_access() -> ModelAccess:
    """The deterministic fake model, which needs no credential and makes no network call."""
    return DirectModelAccess(model="fake:write-file")


class FakeModelE2BProvider(E2BProvider):
    """The production provider; callers that pass no model access get the fake model.

    :param config: Settings from :func:`require_e2b_config`.
    """

    async def ensure(self, *, model_access: Any = resolve_fake_model_access, **kwargs: Any) -> AgentRuntimeHandle:  # type: ignore[override]
        """Provision as in production, defaulting to the fake model."""
        return await super().ensure(model_access=model_access, **kwargs)
