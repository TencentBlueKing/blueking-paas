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

"""会话图片附件：上传、读取、随一轮发出，以及 Runtime 怎么把它取回去。

这里不拉起 agent：会被拒绝的一轮必须在拉起 Runtime 之前就被拒绝。附件真正到达模型的链路在
test_conversations.py 里用真实 agent 验证。
"""

from __future__ import annotations

import json
import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from asgiref.sync import sync_to_async
from django.core.files.uploadedfile import SimpleUploadedFile

from app_spark_api.agent.conversations import attachments as attachment_services
from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.attachments import MAX_ATTACHMENT_SIZE, sniff_image_type
from app_spark_api.agent.conversations.exceptions import AttachmentAlreadyUsedError, AttachmentNotFoundError
from app_spark_api.agent.conversations.models import Conversation, ConversationAttachment, ConversationUserMessage
from app_spark_api.agent.conversations.tokens import mint_state_token
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from tests.api.support import CONVERSATIONS_URL, configure_local_provider, create_reachable_project

if TYPE_CHECKING:
    from pathlib import Path

    from django.test import AsyncClient

    from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db(transaction=True)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture(autouse=True)
def runtime_provider(settings, tmp_path: Path) -> None:
    settings.AGENT_ATTACHMENT_STORAGE = {"backend": "host_tmp_path", "root": str(tmp_path / "attachments")}
    configure_local_provider(settings, tmp_path)
    # direct 下唯一的模型不支持图片，正是拒绝路径要的。
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "deepseek:deepseek-v4-flash", "api_key": "vendor-key"}


@pytest.fixture
def project(bk_user) -> Project:
    return create_reachable_project(bk_user)


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


@pytest.fixture
def other_conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


def build_attachments_url(number: int, suffix: str = "") -> str:
    return f"{CONVERSATIONS_URL}{number}/attachments/{suffix}"


async def upload(client: AsyncClient, number: int, data: bytes = PNG_BYTES) -> Any:
    return await client.post(build_attachments_url(number), {"file": SimpleUploadedFile("shot.png", data)})


async def upload_ok(client: AsyncClient, number: int) -> dict[str, Any]:
    response = await upload(client, number)
    assert response.status_code == HTTPStatus.CREATED, response.content
    return json.loads(response.content)


def bind(conversation: Conversation, *attachment_ids: uuid.UUID | str, run_id: str = "r1") -> ConversationUserMessage:
    return ConversationUserMessage.objects.create_for_conversation(
        conversation, content="", run_id=run_id, attachment_ids=[uuid.UUID(str(i)) for i in attachment_ids]
    )


def fail_upload(*_: Any) -> None:
    raise OSError("disk full")


def make_attachment(conversation: Conversation) -> ConversationAttachment:
    backend, config = attachment_services.blob_location(conversation.id, uuid.uuid4())
    return ConversationAttachment.objects.create(
        conversation=conversation, filename="a.png", mime_type="image/png", size=1, sha256="0" * 64,
        backend=backend, config=config,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (PNG_BYTES, "image/png"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        (b"GIF89a", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"RIFF\x00\x00\x00\x00WAVEfmt ", None),
        (b"<svg xmlns='http://www.w3.org/2000/svg'>", None),
    ],
)
def test_the_type_comes_from_the_file_header(head: bytes, expected: str | None) -> None:
    assert sniff_image_type(head) == expected


def test_bkrepo_keys_are_scoped_by_conversation(settings) -> None:
    settings.AGENT_ATTACHMENT_STORAGE = {"backend": "bk_repo", "root": "spark-attachments"}
    conversation_id, attachment_id = uuid.uuid4(), uuid.uuid4()

    assert attachment_services.blob_location(conversation_id, attachment_id) == (
        "bk_repo",
        {"bucket": "spark-attachments", "key": f"attachments/{conversation_id}/{attachment_id}"},
    )


async def test_an_uploaded_image_can_be_read_back_and_shows_in_history(
    aapi_client, conversation, other_conversation
) -> None:
    body = await upload_ok(aapi_client, conversation.number)

    assert (body["filename"], body["mime_type"], body["size"]) == ("shot.png", "image/png", len(PNG_BYTES))
    assert body["url"] == build_attachments_url(conversation.number, f"{body['id']}/content/")
    detail = await aapi_client.get(build_attachments_url(conversation.number, f"{body['id']}/"))
    assert json.loads(detail.content) == body

    content = await aapi_client.get(body["url"])
    assert content.content == PNG_BYTES
    assert content["Content-Type"] == "image/png"
    assert content["Cache-Control"] == "private, max-age=31536000, immutable"
    assert content["X-Content-Type-Options"] == "nosniff"

    # 换一个会话的路径去读，附件就不存在。
    foreign = await aapi_client.get(build_attachments_url(other_conversation.number, f"{body['id']}/content/"))
    assert json.loads(foreign.content)["code"] == "ATTACHMENT_NOT_FOUND"

    await sync_to_async(bind)(conversation, body["id"])
    history = await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/")
    assert [r["user_message"]["attachments"] for r in json.loads(history.content)["records"]] == [[body]]


async def test_history_lists_images_in_the_order_they_were_sent(aapi_client, conversation) -> None:
    """模型按 attachment_ids 的顺序看图，历史得一样：「第一张图」在两边说的才是同一张。"""
    uploaded_first = await upload_ok(aapi_client, conversation.number)
    uploaded_second = await upload_ok(aapi_client, conversation.number)

    await sync_to_async(bind)(conversation, uploaded_second["id"], uploaded_first["id"])

    history = await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/")
    [record] = json.loads(history.content)["records"]
    assert [a["id"] for a in record["user_message"]["attachments"]] == [uploaded_second["id"], uploaded_first["id"]]


async def test_deleting_a_projects_conversations_deletes_their_image_bytes(aapi_client, project, conversation) -> None:
    body = await upload_ok(aapi_client, conversation.number)
    attachment = await ConversationAttachment.objects.aget(id=body["id"])
    blob = attachment.get_blob_store()
    assert blob.get_bytes() == PNG_BYTES

    await services.adelete_project_conversations(project.id)

    assert not await ConversationAttachment.objects.aexists()
    with pytest.raises(FileNotFoundError):
        blob.get_bytes()


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("not-image", "ATTACHMENT_TYPE_UNSUPPORTED"),
        ("too-large", "ATTACHMENT_TOO_LARGE"),
        ("closed", "CONVERSATION_CLOSED"),
        ("storage-down", "ATTACHMENT_STORAGE_UNAVAILABLE"),
    ],
)
async def test_a_refused_upload_stores_nothing(aapi_client, conversation, monkeypatch, case: str, code: str) -> None:
    data = {"not-image": b"just some text, honest", "too-large": PNG_BYTES + b"\x00" * MAX_ATTACHMENT_SIZE}
    if case == "closed":
        await aapi_client.post(f"{CONVERSATIONS_URL}{conversation.number}/close/")

    if case == "storage-down":
        monkeypatch.setattr("app_spark_api.repository.storage.blob_stores.HostTmpPath.upload", fail_upload)

    response = await upload(aapi_client, conversation.number, data.get(case, PNG_BYTES))

    assert json.loads(response.content)["code"] == code
    assert not await ConversationAttachment.objects.aexists()


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="nothing"),
        pytest.param({"content": "   "}, id="blank-text-only"),
        pytest.param({"content": "hi", "attachment_ids": [str(uuid.UUID(int=1))] * 2}, id="duplicate-ids"),
        pytest.param({"content": "hi", "attachment_ids": [str(uuid.uuid4()) for _ in range(4)]}, id="too-many"),
    ],
)
async def test_a_malformed_turn_is_refused(aapi_client, conversation, payload: dict[str, Any]) -> None:
    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/", data=payload, content_type="application/json"
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, response.content


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("model-cannot-read-images", "MODEL_IMAGE_INPUT_UNSUPPORTED"),
        ("another-conversations-attachment", "ATTACHMENT_NOT_FOUND"),
        ("already-sent", "ATTACHMENT_ALREADY_USED"),
    ],
)
async def test_an_unsendable_attachment_is_refused_before_a_runtime_starts(
    aapi_client, conversation, other_conversation, case: str, code: str
) -> None:
    # direct 的模型不支持图片；后两种情况报的是附件错误，说明附件先于模型能力检查。
    owner = other_conversation if case == "another-conversations-attachment" else conversation
    body = await upload_ok(aapi_client, owner.number)
    if case == "already-sent":
        await sync_to_async(bind)(conversation, body["id"])

    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/",
        data={"content": "", "attachment_ids": [body["id"]]},
        content_type="application/json",
    )

    assert json.loads(response.content)["code"] == code
    assert await get_agent_runtime_provider().peek(str(conversation.id)) is None


def test_binding_is_exclusive_and_freed_when_the_message_goes(conversation, other_conversation) -> None:
    first, second = make_attachment(conversation), make_attachment(conversation)
    message = bind(conversation, first.id, second.id)
    assert set(message.attachments.values_list("id", flat=True)) == {first.id, second.id}

    with pytest.raises(AttachmentAlreadyUsedError):
        bind(conversation, first.id, run_id="r2")
    assert not ConversationUserMessage.objects.filter(run_id="r2").exists()

    with pytest.raises(AttachmentNotFoundError):
        bind(other_conversation, first.id, run_id="r3")

    # start_run 在 Runtime 拒绝时删掉这条消息，附件要回到未使用状态，让用户原样重发。
    message.delete()
    first.refresh_from_db()
    assert first.user_message_id is None
    bind(conversation, first.id, run_id="r4")


async def test_only_the_conversations_current_runtime_reads_its_attachments(
    aapi_client, conversation, other_conversation
) -> None:
    body = await upload_ok(aapi_client, conversation.number)

    async def read(path_conversation: Conversation, token: str) -> Any:
        url = f"/api/internal/conversations/{path_conversation.id}/state/attachments/{body['id']}/content"
        return await aapi_client.get(url, headers={"Authorization": f"Bearer {token}"})

    own_token = mint_state_token(conversation.id, epoch=conversation.state_epoch)
    other_token = mint_state_token(other_conversation.id, epoch=other_conversation.state_epoch)
    own = await read(conversation, own_token)
    assert (own.status_code, own.content, own["Content-Type"]) == (HTTPStatus.OK, PNG_BYTES, "image/png")
    assert (await read(conversation, other_token)).status_code == HTTPStatus.NOT_FOUND
    assert (await read(other_conversation, other_token)).status_code == HTTPStatus.NOT_FOUND

    # 吊销之后，原来那张 token 立即读不到。
    await services.revoke_state_access(conversation)
    assert (await read(conversation, own_token)).status_code == HTTPStatus.NOT_FOUND
