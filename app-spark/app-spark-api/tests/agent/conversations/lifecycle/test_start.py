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

"""Starting a turn: what is recorded before the Runtime gets it, and what the Runtime is told.

The Runtime is a stand-in here; the end-to-end versions, with a real agent, are in
``tests/api/test_conversations.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.lifecycle import start
from app_spark_api.agent.conversations.models import Conversation, ConversationUserMessage
from app_spark_api.agent.model_catalog import services as model_catalog_services
from app_spark_api.core.projects.models import Project
from app_spark_api.infras.bkaidev import GatewayModel
from tests.agent.conversations.support import HANDLE, FakeClient, FakeProvider, FakeRun, install_fake_provider

if TYPE_CHECKING:
    from app_spark_api.agent.runtime import RuntimeHealth

# start_run writes the user message through the async ORM, on a connection of its own: rows left
# uncommitted in the test's transaction would be invisible to it, or lock it out.
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def provider(monkeypatch) -> FakeProvider:
    return install_fake_provider(monkeypatch)


@pytest.fixture
def conversation(bk_user) -> Conversation:
    project = Project.objects.create(
        id="lifecycle-start",
        name="Lifecycle Start",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


async def test_a_turn_can_be_stopped_as_soon_as_its_runtime_has_it(provider, conversation, monkeypatch):
    """/health 报出 run_id 的那一刻前端就可能拿它来停，所以 Runtime 收到这一轮之前，归属就得已经落库。"""
    owned_when_started: list[bool] = []

    class StartingClient(FakeClient):
        async def start_run(
            self,
            *,
            content: str,
            context_version: int,
            run_id: str,
            model_id: str | None = None,
            images: Any = (),
        ) -> FakeRun:
            owned = ConversationUserMessage.objects.filter(conversation=conversation, run_id=run_id)
            owned_when_started.append(await owned.aexists())
            run = FakeRun([])
            run.run_id = run_id
            return run

    async def open_client(_conversation: Conversation, **_kwargs: Any) -> StartingClient:
        return StartingClient(HANDLE)

    async def already_warm(_conversation: Conversation, _client: Any, health: RuntimeHealth) -> RuntimeHealth:
        return health

    monkeypatch.setattr(start, "open_client", open_client)
    monkeypatch.setattr(start, "resume_if_cold", already_warm)

    run = await start.start_run(conversation, content="hi")

    assert owned_when_started == [True]
    await services.stop_run(conversation, run.run_id)
    assert FakeClient.stopped == [run.run_id]


async def test_a_turn_that_names_a_model_reaches_the_runtime(provider, conversation, settings, monkeypatch):
    """用户选的模型要原样交给 Runtime。"""
    settings.AGENT_MODEL_SOURCE = "bkaidev"
    settings.BKAIDEV_MODEL_CONFIG = {"default_model_id": "hy3", "available_models": ["hy3"]}
    seen: list[str | None] = []

    async def fetch_gateway_models(*_args: Any, **_kwargs: Any) -> list[GatewayModel]:
        return [GatewayModel(id="hy3")]

    monkeypatch.setattr(model_catalog_services, "_fetch_gateway_models", fetch_gateway_models)

    class StartingClient(FakeClient):
        async def start_run(
            self,
            *,
            content: str,
            context_version: int,
            run_id: str,
            model_id: str | None = None,
            images: Any = (),
        ) -> FakeRun:
            seen.append(model_id)
            run = FakeRun([])
            run.run_id = run_id
            return run

    async def open_client(_conversation: Conversation, **_kwargs: Any) -> StartingClient:
        return StartingClient(HANDLE)

    async def already_warm(_conversation: Conversation, _client: Any, health: RuntimeHealth) -> RuntimeHealth:
        return health

    monkeypatch.setattr(start, "open_client", open_client)
    monkeypatch.setattr(start, "resume_if_cold", already_warm)

    await start.start_run(conversation, content="hi", model_id="hy3")

    assert seen == ["hy3"]
