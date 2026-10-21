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

"""Turning settings into a provider, including when the settings are wrong."""

from __future__ import annotations

import pytest

from app_spark_api.agent.runtime.exceptions import AgentConfigurationError
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider, make_agent_runtime_provider
from app_spark_api.agent.runtime.providers.local import LocalProcessProvider

CONFIG = {
    "agent_project_dir": "/srv/app-spark/agent",
    "workspace_root": "/var/lib/app-spark/workspaces",
    "state_root": "/var/lib/app-spark/agent-state",
}


def test_the_local_provider_is_built_from_its_configuration():
    provider = make_agent_runtime_provider("local_process", CONFIG)

    assert isinstance(provider, LocalProcessProvider)
    assert provider.config.agent_project_dir == CONFIG["agent_project_dir"]


def test_an_unknown_provider_is_refused_by_name():
    with pytest.raises(AgentConfigurationError, match="sandbox_over_grpc"):
        make_agent_runtime_provider("sandbox_over_grpc", CONFIG)


def test_a_provider_with_unusable_configuration_is_refused():
    with pytest.raises(AgentConfigurationError, match="state_root"):
        make_agent_runtime_provider("local_process", {k: v for k, v in CONFIG.items() if k != "state_root"})


def test_changing_the_settings_builds_a_new_provider(settings):
    settings.AGENT_RUNTIME_PROVIDER = "local_process"
    settings.AGENT_RUNTIME_PROVIDER_CONFIG = CONFIG
    first = get_agent_runtime_provider()

    settings.AGENT_RUNTIME_PROVIDER_CONFIG = {**CONFIG, "state_root": "/var/lib/app-spark/elsewhere"}
    second = get_agent_runtime_provider()

    assert second is not first
    assert isinstance(second, LocalProcessProvider)
    assert second.config.state_root == "/var/lib/app-spark/elsewhere"
