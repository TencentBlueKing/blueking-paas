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

from datetime import timedelta

import pytest
from django.utils import timezone

from app_spark_api.agent.conversations import state
from app_spark_api.agent.conversations.models import Conversation, ConversationNumber, ConversationUserMessage
from app_spark_api.agent.conversations.services import aclose_project_conversations, delete_project_conversations
from app_spark_api.agent.conversations.state_models import (
    ConversationCheckpoint,
    ConversationContextVersion,
    ConversationMessage,
    ConversationUiEvent,
)
from app_spark_api.repository.storage.blob_stores import HostTmpPath

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def context_storage(settings, tmp_path) -> None:
    settings.AGENT_CONTEXT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "blobs")}


def make_conversation(project, bk_user) -> Conversation:
    conversation = Conversation.objects.create_for_project(project, owner=bk_user.pk)
    ConversationUserMessage.objects.create_for_conversation(conversation, content="build an app")
    state.append_records(
        conversation.id,
        state.MESSAGE_CHANNEL,
        [{"seq": 1, "run_id": "run-a", "timestamp": "2026-01-01T00:00:00+00:00", "message": {"n": 1}}],
    )
    state.append_records(
        conversation.id,
        state.UI_EVENT_CHANNEL,
        [{"seq": 1, "run_id": "run-a", "timestamp": "2026-01-01T00:00:00+00:00", "event": {"type": "DONE"}}],
    )
    state.save_context(conversation.id, {"context_version": 1, "messages": []})
    ConversationCheckpoint.objects.create(
        conversation=conversation,
        run_id="run-a",
        commit="a" * 40,
        tag="checkpoint-a",
        context_version=1,
    )

    return conversation


async def test_closing_project_conversations_ends_live_ones_and_revokes_their_tokens(project, bk_user):
    closed_before = timezone.now() - timedelta(days=1)
    live = await Conversation.objects.acreate(project=project, number=1, owner=bk_user, tenant_id=project.tenant_id)
    closed = await Conversation.objects.acreate(
        project=project,
        number=2,
        owner=bk_user,
        tenant_id=project.tenant_id,
        closed_at=closed_before,
    )

    await aclose_project_conversations(project.id)

    await live.arefresh_from_db()
    await closed.arefresh_from_db()
    assert live.closed_at is not None
    assert live.state_epoch == 2
    # 已经结束的会话不再动：结束时间保持原样，它的回写凭证早在结束时就吊销过了。
    assert (closed.closed_at, closed.state_epoch) == (closed_before, 1)


def test_delete_project_conversations_removes_history_and_blobs_but_keeps_counter(project, bk_user):
    conversation = make_conversation(project, bk_user)
    version = ConversationContextVersion.objects.get(conversation=conversation)
    store = version.get_blob_store()
    assert isinstance(store, HostTmpPath)
    assert store.path.exists()

    delete_project_conversations(project.id)

    assert not Conversation.objects.filter(project=project).exists()
    assert not ConversationUserMessage.objects.filter(conversation_id=conversation.id).exists()
    assert not ConversationMessage.objects.filter(conversation_id=conversation.id).exists()
    assert not ConversationUiEvent.objects.filter(conversation_id=conversation.id).exists()
    assert not ConversationCheckpoint.objects.filter(conversation_id=conversation.id).exists()
    assert not ConversationContextVersion.objects.filter(conversation_id=conversation.id).exists()
    assert not store.path.exists()
    assert ConversationNumber.objects.filter(project=project).exists()


def test_delete_project_conversations_keeps_locations_when_blob_delete_fails(project, bk_user, monkeypatch):
    conversation = make_conversation(project, bk_user)
    version = ConversationContextVersion.objects.get(conversation=conversation)
    store = version.get_blob_store()
    assert isinstance(store, HostTmpPath)
    real_delete = HostTmpPath.delete

    def fail_delete(self) -> None:
        raise OSError("storage unavailable")

    monkeypatch.setattr(HostTmpPath, "delete", fail_delete)

    with pytest.raises(OSError, match="storage unavailable"):
        delete_project_conversations(project.id)

    assert Conversation.objects.filter(pk=conversation.id).exists()
    assert ConversationContextVersion.objects.filter(pk=version.pk).exists()
    assert store.path.exists()

    monkeypatch.setattr(HostTmpPath, "delete", real_delete)
    delete_project_conversations(project.id)

    assert not Conversation.objects.filter(pk=conversation.id).exists()
    assert not store.path.exists()
