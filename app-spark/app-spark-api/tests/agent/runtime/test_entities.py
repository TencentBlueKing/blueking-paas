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

"""Configuration that cannot be trusted, and responses that cannot be believed."""

from __future__ import annotations

import pytest

from app_spark_api.agent.runtime.entities import (
    EventPage,
    RuntimeHealth,
    structure_local_process_config,
)
from app_spark_api.agent.runtime.exceptions import AgentConfigurationError, AgentUnavailableError

MINIMAL_CONFIG = {
    "agent_project_dir": "/srv/app-spark/agent",
    "workspace_root": "/var/lib/app-spark/workspaces",
    "state_root": "/var/lib/app-spark/agent-state",
}

HEALTHY_PAYLOAD = {
    "status": "ok",
    "model": "fake:write-file",
    "conversation_id": "3f2b",
    "context_version": 2,
    "log_seq": 8,
    "ui_event_seq": 18,
    "running": False,
}


def test_a_minimal_configuration_gets_workable_defaults():
    config = structure_local_process_config(MINIMAL_CONFIG)

    assert config.agent_project_dir == "/srv/app-spark/agent"
    # Unset means "leave it to the agent's own default" rather than "send an empty value".
    assert config.model is None
    assert config.model_api_key is None
    assert config.extra_env == {}
    assert config.startup_timeout_seconds > 0


def test_every_setting_can_be_given():
    config = structure_local_process_config(
        {
            **MINIMAL_CONFIG,
            "model": "deepseek:deepseek-v4-flash",
            "model_api_key": "a-key",
            "startup_timeout_seconds": 5.0,
            "extra_env": {"APP_SPARK_AGENT_FAKE_DELAY_SECONDS": "1"},
        }
    )

    assert config.model == "deepseek:deepseek-v4-flash"
    assert config.model_api_key == "a-key"
    assert config.startup_timeout_seconds == 5.0
    assert config.extra_env == {"APP_SPARK_AGENT_FAKE_DELAY_SECONDS": "1"}


@pytest.mark.parametrize(
    ("raw_config", "reason"),
    [
        pytest.param(
            {k: v for k, v in MINIMAL_CONFIG.items() if k != "state_root"},
            "state_root",
            id="a-missing-field",
        ),
        pytest.param(
            {**MINIMAL_CONFIG, "workspace_root": ""},
            "workspace_root",
            id="an-empty-path",
        ),
        pytest.param(
            {**MINIMAL_CONFIG, "startup_timeout_seconds": "soon"},
            "startup_timeout_seconds",
            id="an-unparseable-number",
        ),
        # A typo in a settings file is otherwise silently ignored, and the operator is left
        # wondering why the value they wrote had no effect.
        pytest.param(
            {**MINIMAL_CONFIG, "workspce_root": "/tmp"},
            "workspce_root",
            id="a-misspelled-key",
        ),
        pytest.param("just a string", "LocalProcessConfig", id="not-a-mapping"),
    ],
)
def test_an_unusable_configuration_is_refused_by_name(raw_config, reason):
    with pytest.raises(AgentConfigurationError) as exc_info:
        structure_local_process_config(raw_config)

    assert reason in str(exc_info.value)


def test_a_health_snapshot_is_read_from_the_runtimes_own_words():
    health = RuntimeHealth.from_payload(HEALTHY_PAYLOAD)

    assert health.model == "fake:write-file"
    assert health.conversation_id == "3f2b"
    assert health.context_version == 2
    assert health.running is False


def test_a_runtime_that_has_never_run_has_no_conversation_yet():
    health = RuntimeHealth.from_payload({**HEALTHY_PAYLOAD, "conversation_id": None})

    assert health.conversation_id is None


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({k: v for k, v in HEALTHY_PAYLOAD.items() if k != "log_seq"}, id="truncated"),
        pytest.param({**HEALTHY_PAYLOAD, "context_version": "two"}, id="wrongly-typed"),
        pytest.param(["not", "an", "object"], id="not-an-object"),
    ],
)
def test_an_unreadable_health_response_is_not_passed_on(payload):
    """Something is answering on that port, but it is not an Agent Runtime.

    Worth its own error rather than an AttributeError three frames later: this is what a stale
    port or a proxy in the way actually looks like.
    """
    with pytest.raises(AgentUnavailableError):
        RuntimeHealth.from_payload(payload)


def test_a_page_knows_whether_it_reached_the_end_of_the_channel():
    assert EventPage.from_payload({"since": 0, "last_seq": 2, "records": []}).exhausted is True
    assert EventPage.from_payload({"since": 0, "last_seq": 2, "records": [{"seq": 1}, {"seq": 2}]}).exhausted is True
    assert EventPage.from_payload({"since": 0, "last_seq": 9, "records": [{"seq": 1}]}).exhausted is False


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"since": 0, "last_seq": 2}, id="no-records"),
        pytest.param({"since": 0, "last_seq": 2, "records": {}}, id="records-not-a-list"),
        pytest.param("nonsense", id="not-an-object"),
    ],
)
def test_an_unreadable_drain_response_is_not_passed_on(payload):
    with pytest.raises(AgentUnavailableError):
        EventPage.from_payload(payload)
