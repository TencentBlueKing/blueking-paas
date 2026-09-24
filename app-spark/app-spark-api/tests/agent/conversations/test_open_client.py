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

"""open_client leaves resolving model access to the provider, bound to the caller's login."""

from typing import Any

import pytest

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.runtime import AgentRuntimeHandle, BkAidevModelAccess, GitRemote
from app_spark_api.infras.bk_access_token import UserCredential, UserCredentialType

CREDENTIAL = UserCredential(type=UserCredentialType.BK_TICKET, value="login-cookie", username="alice")
MODEL_ACCESS = BkAidevModelAccess(
    base_url="https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1",
    model_name="deepseek-v4-flash",
    access_token="user-token",
)
REMOTE = GitRemote(clone_url="http://git.example/p.git", branch="main", username="bot", token="repo-token")


class RecordingProvider:
    """A provider that remembers what ensure was given, and never starts anything."""

    def __init__(self) -> None:
        self.ensure_calls: list[dict[str, Any]] = []

    async def ensure(self, **kwargs: Any) -> AgentRuntimeHandle:
        self.ensure_calls.append(kwargs)
        return AgentRuntimeHandle(
            conversation_id=kwargs["conversation_id"], base_url="http://127.0.0.1:1", runtime_token="t"
        )


@pytest.fixture()
def resolved_credentials(monkeypatch) -> list[UserCredential | None]:
    """Credentials a model access resolver was called with, with the repository always ready."""
    calls: list[UserCredential | None] = []

    async def resolve(credential: UserCredential | None) -> BkAidevModelAccess:
        calls.append(credential)
        return MODEL_ACCESS

    async def ready_repository(project_id: str) -> object:
        return object()

    monkeypatch.setattr(services, "resolve_model_access", resolve)
    monkeypatch.setattr(services, "arequire_project_git_ready", ready_repository)
    monkeypatch.setattr(services, "_git_remote", lambda _repo: REMOTE)
    return calls


@pytest.fixture()
def provider(monkeypatch) -> RecordingProvider:
    """Make open_client drive a RecordingProvider."""
    recording = RecordingProvider()
    monkeypatch.setattr(services, "get_agent_runtime_provider", lambda: recording)
    return recording


async def test_opening_a_client_does_not_resolve_model_access_itself(provider, resolved_credentials):
    # Every turn goes through open_client. Resolving here would cost a token exchange per message
    # even when the Runtime is already up; only the provider knows whether it is starting one.
    await services.open_client(Conversation(project_id="p"), credential=CREDENTIAL)

    assert resolved_credentials == []


async def test_the_provider_resolves_model_access_with_the_callers_login(provider, resolved_credentials):
    await services.open_client(Conversation(project_id="p"), credential=CREDENTIAL)

    access = await provider.ensure_calls[0]["model_access"]()

    assert access == MODEL_ACCESS
    assert resolved_credentials == [CREDENTIAL]
