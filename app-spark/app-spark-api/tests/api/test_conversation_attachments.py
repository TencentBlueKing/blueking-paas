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

"""会话文件附件：上传、读取、随一轮发出，以及 Runtime 从哪下载它。

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
from blue_krill.web.std_error import APIError
from django.core.files.uploadedfile import SimpleUploadedFile

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.attachment_storage import (
    BkRepoAttachmentStorage,
    HostTmpPathAttachmentStorage,
    resolve_attachment_storage,
)
from app_spark_api.agent.conversations.attachments import MAX_ATTACHMENT_SIZE, detect_mime_type, normalize_extension
from app_spark_api.agent.conversations.models import Conversation, ConversationAttachment, ConversationUserMessage
from app_spark_api.agent.conversations.tokens import mint_state_token
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils.api_errors.error_codes import error_codes
from tests.api.support import CONVERSATIONS_URL, configure_local_provider, create_reachable_project

if TYPE_CHECKING:
    from pathlib import Path

    from django.test import AsyncClient

    from app_spark_api.core.projects.models import Project

pytestmark = pytest.mark.django_db(transaction=True)

# 能被 magika 认出来的最小 PNG：只有文件头而没有像素数据的字节，按内容识别不出是图片。
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8ffff3f0005fe02fe0dd1a2e60000000049454e44ae426082"
)
CSV_BYTES = b"name,age\nbob,3\nal,4\ncarol,5\n"


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


def build_internal_url(conversation: Conversation, suffix: str) -> str:
    return f"/api/internal/conversations/{conversation.id}/state/attachments/{suffix}"


async def upload(client: AsyncClient, number: int, data: bytes = PNG_BYTES, filename: str = "shot.png") -> Any:
    return await client.post(build_attachments_url(number), {"file": SimpleUploadedFile(filename, data)})


async def upload_ok(client: AsyncClient, number: int, data: bytes = PNG_BYTES, filename: str = "shot.png") -> Any:
    response = await upload(client, number, data, filename)
    assert response.status_code == HTTPStatus.CREATED, response.content
    return json.loads(response.content)


def bind(conversation: Conversation, *attachment_ids: uuid.UUID | str, run_id: str = "r1") -> ConversationUserMessage:
    return ConversationUserMessage.objects.create_for_conversation(
        conversation, content="", run_id=run_id, attachment_ids=[uuid.UUID(str(i)) for i in attachment_ids]
    )


def fail_upload(*_: Any) -> None:
    raise OSError("disk full")


def make_attachment(conversation: Conversation) -> ConversationAttachment:
    return ConversationAttachment.objects.create(
        conversation=conversation, filename="a.png", mime_type="image/png", size=1, sha256="0" * 64,
        backend="host_tmp_path", config={"path": "/nonexistent"},
    )  # fmt: skip


@pytest.mark.parametrize(
    ("data", "filename", "expected"),
    [
        pytest.param(PNG_BYTES, "shot.png", "image/png", id="content-and-extension-agree"),
        pytest.param(PNG_BYTES, "shot", "image/png", id="no-extension"),
        pytest.param(PNG_BYTES, "shot.txt", "image/png", id="specific-content-beats-the-extension"),
        pytest.param(CSV_BYTES, "data.csv", "text/csv", id="csv"),
        pytest.param(b"# Notes\n\nSome *markdown* here.\n", "notes.md", "text/markdown", id="generic-text-uses-ext"),
        pytest.param(b"just some text, honest", "fake.png", "text/plain", id="an-extension-never-makes-an-image"),
    ],
)
def test_the_type_comes_from_the_content_first_and_the_extension_second(
    data: bytes, filename: str, expected: str
) -> None:
    assert detect_mime_type(data, normalize_extension(filename)) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("Report.CSV", ".csv"),
        ("archive.tar.gz", ".gz"),
        ("README", ""),
        ("evil.p/../hp", ""),
        ("a." + "x" * 17, ""),
        ("a.c++", ""),
    ],
)
def test_only_short_alphanumeric_extensions_are_kept(filename: str, expected: str) -> None:
    assert normalize_extension(filename) == expected


def test_each_backend_places_attachments_in_its_own_way() -> None:
    conversation_id, attachment_id = uuid.uuid4(), uuid.uuid4()

    assert HostTmpPathAttachmentStorage().locate("/data/att/", conversation_id, attachment_id, ".csv") == {
        "path": f"/data/att/{conversation_id}/{attachment_id}.csv"
    }
    assert BkRepoAttachmentStorage().locate("spark-attachments", conversation_id, attachment_id, ".csv") == {
        "bucket": "spark-attachments",
        "key": f"attachments/{conversation_id}/{attachment_id}.csv",
    }


def test_an_unknown_backend_is_a_configuration_error() -> None:
    with pytest.raises(StorageConfigurationError):
        resolve_attachment_storage("s3")


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
    assert content["Content-Disposition"].startswith("inline")

    # 换一个会话的路径去读，附件就不存在。
    foreign = await aapi_client.get(build_attachments_url(other_conversation.number, f"{body['id']}/content/"))
    assert json.loads(foreign.content)["code"] == "ATTACHMENT_NOT_FOUND"

    await sync_to_async(bind)(conversation, body["id"])
    history = await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/")
    assert [r["user_message"]["attachments"] for r in json.loads(history.content)["records"]] == [[body]]


@pytest.mark.parametrize(
    ("data", "filename", "mime_type"),
    [
        pytest.param(CSV_BYTES, "data.csv", "text/csv", id="csv"),
        pytest.param(b"<html><script>alert(1)</script></html>", "page.html", "text/html", id="html"),
    ],
)
async def test_a_non_image_file_is_accepted_and_served_as_a_download(
    aapi_client, conversation, data: bytes, filename: str, mime_type: str
) -> None:
    """HTML 在本服务的源下内联打开会执行脚本，所以图片以外一律按下载处理。"""
    body = await upload_ok(aapi_client, conversation.number, data, filename)

    assert body["mime_type"] == mime_type
    attachment = await ConversationAttachment.objects.aget(id=body["id"])
    assert attachment.extension == f".{filename.rsplit('.', 1)[1]}"
    assert attachment.config["path"].endswith(f"{attachment.id}{attachment.extension}")

    content = await aapi_client.get(body["url"])
    assert content.content == data
    assert content["Content-Disposition"] == f'attachment; filename="{filename}"'
    assert content["Content-Security-Policy"] == "sandbox"


async def test_an_image_without_a_filename_is_still_served_inline(aapi_client, conversation) -> None:
    """Django 对空文件名的 inline 返回 None，不能让响应头变成字面上的 "None"。"""
    body = await upload_ok(aapi_client, conversation.number)
    await ConversationAttachment.objects.filter(id=body["id"]).aupdate(filename="")

    content = await aapi_client.get(body["url"])

    assert content["Content-Disposition"] == "inline"
    assert "Content-Security-Policy" not in content


async def test_history_lists_attachments_in_the_order_they_were_sent(aapi_client, conversation) -> None:
    """模型按 attachment_ids 的顺序看附件，历史得一样：「第一个附件」在两边说的才是同一个。"""
    uploaded_first = await upload_ok(aapi_client, conversation.number)
    uploaded_second = await upload_ok(aapi_client, conversation.number)

    await sync_to_async(bind)(conversation, uploaded_second["id"], uploaded_first["id"])

    history = await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/")
    [record] = json.loads(history.content)["records"]
    assert [a["id"] for a in record["user_message"]["attachments"]] == [uploaded_second["id"], uploaded_first["id"]]


async def test_deleting_a_projects_conversations_deletes_their_attachment_bytes(
    aapi_client, project, conversation
) -> None:
    body = await upload_ok(aapi_client, conversation.number)
    attachment = await ConversationAttachment.objects.aget(id=body["id"])
    blob = attachment.get_blob_store()
    assert blob.get_bytes() == PNG_BYTES

    await services.adelete_project_conversations(project.id)

    assert not await ConversationAttachment.objects.aexists()
    with pytest.raises(FileNotFoundError):
        blob.get_bytes()


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("too-large", error_codes.ATTACHMENT_TOO_LARGE),
        ("closed", error_codes.CONVERSATION_CLOSED),
        ("storage-down", error_codes.ATTACHMENT_STORAGE_UNAVAILABLE),
    ],
)
async def test_a_refused_upload_stores_nothing(
    aapi_client, conversation, monkeypatch, case: str, expected: APIError
) -> None:
    data = {"too-large": PNG_BYTES + b"\x00" * MAX_ATTACHMENT_SIZE}
    if case == "closed":
        await aapi_client.post(f"{CONVERSATIONS_URL}{conversation.number}/close/")

    if case == "storage-down":
        monkeypatch.setattr("app_spark_api.repository.storage.blob_stores.HostTmpPath.upload", fail_upload)

    response = await upload(aapi_client, conversation.number, data.get(case, PNG_BYTES))

    assert (response.status_code, json.loads(response.content)["code"]) == (expected.status_code, expected.code)
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
    ("case", "expected"),
    [
        ("model-cannot-read-images", error_codes.MODEL_IMAGE_INPUT_UNSUPPORTED),
        ("another-conversations-attachment", error_codes.ATTACHMENT_NOT_FOUND),
        ("already-sent", error_codes.ATTACHMENT_ALREADY_USED),
    ],
)
async def test_an_unsendable_attachment_is_refused_before_a_runtime_starts(
    aapi_client, conversation, other_conversation, case: str, expected: APIError
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

    assert (response.status_code, json.loads(response.content)["code"]) == (expected.status_code, expected.code)
    assert await get_agent_runtime_provider().peek(str(conversation.id)) is None


def test_binding_is_exclusive_and_freed_when_the_message_goes(conversation, other_conversation) -> None:
    first, second = make_attachment(conversation), make_attachment(conversation)
    message = bind(conversation, first.id, second.id)
    assert set(message.attachments.values_list("id", flat=True)) == {first.id, second.id}

    with pytest.raises(APIError) as already_used:
        bind(conversation, first.id, run_id="r2")
    assert already_used.value.code == "ATTACHMENT_ALREADY_USED"
    assert not ConversationUserMessage.objects.filter(run_id="r2").exists()

    with pytest.raises(APIError) as not_found:
        bind(other_conversation, first.id, run_id="r3")
    assert not_found.value.code == "ATTACHMENT_NOT_FOUND"

    # start_run 在 Runtime 拒绝时删掉这条消息，附件要回到未使用状态，让用户原样重发。
    message.delete()
    first.refresh_from_db()
    assert first.user_message_id is None
    bind(conversation, first.id, run_id="r4")


async def test_only_the_conversations_current_runtime_reads_its_attachments(
    aapi_client, conversation, other_conversation
) -> None:
    body = await upload_ok(aapi_client, conversation.number, CSV_BYTES, "data.csv")

    async def read(path_conversation: Conversation, token: str, suffix: str) -> Any:
        url = build_internal_url(path_conversation, suffix)
        return await aapi_client.get(url, headers={"Authorization": f"Bearer {token}"})

    own_token = mint_state_token(conversation.id, epoch=conversation.state_epoch)
    other_token = mint_state_token(other_conversation.id, epoch=other_conversation.state_epoch)

    # host_tmp_path 没有第三方能签地址，Runtime 被指回本服务的内容接口，要带 token。
    meta = await read(conversation, own_token, f"{body['id']}/")
    assert json.loads(meta.content) == {
        "filename": "data.csv",
        "mime_type": "text/csv",
        "size": len(CSV_BYTES),
        "source": {"url": f"attachments/{body['id']}/content", "authenticated": True},
    }
    own = await read(conversation, own_token, f"{body['id']}/content")
    assert (own.status_code, own.content, own["Content-Type"]) == (HTTPStatus.OK, CSV_BYTES, "text/csv")

    for path_conversation, token in ((conversation, other_token), (other_conversation, other_token)):
        for suffix in (f"{body['id']}/", f"{body['id']}/content"):
            assert (await read(path_conversation, token, suffix)).status_code == HTTPStatus.NOT_FOUND

    # 吊销之后，原来那张 token 立即读不到。
    await services.revoke_state_access(conversation)
    assert (await read(conversation, own_token, f"{body['id']}/")).status_code == HTTPStatus.NOT_FOUND


async def test_a_bkrepo_attachment_is_downloaded_directly_from_bkrepo(
    aapi_client, settings, fake_bkrepo, conversation
) -> None:
    """字节不经过本服务：Runtime 拿到短时效的预签名地址，且不能带 token 去请求它。"""
    settings.AGENT_ATTACHMENT_STORAGE = {"backend": "bk_repo", "root": "spark-attachments"}
    body = await upload_ok(aapi_client, conversation.number, CSV_BYTES, "data.csv")
    key = f"attachments/{conversation.id}/{body['id']}.csv"
    assert fake_bkrepo.objects[("spark-attachments", key)] == CSV_BYTES

    # 换回本机存储后，老附件仍按自己行里记下的后端处理。
    settings.AGENT_ATTACHMENT_STORAGE = {"backend": "host_tmp_path", "root": "/tmp/elsewhere"}
    token = mint_state_token(conversation.id, epoch=conversation.state_epoch)
    meta = await aapi_client.get(
        build_internal_url(conversation, f"{body['id']}/"), headers={"Authorization": f"Bearer {token}"}
    )

    source = json.loads(meta.content)["source"]
    assert source["authenticated"] is False
    assert source["url"].startswith("https://bkrepo.example.com/")
    assert fake_bkrepo.signed == [("spark-attachments", key, 300)]


async def test_a_bkrepo_that_cannot_sign_is_reported_as_storage_unavailable(
    aapi_client, settings, fake_bkrepo, conversation
) -> None:
    settings.AGENT_ATTACHMENT_STORAGE = {"backend": "bk_repo", "root": "spark-attachments"}
    body = await upload_ok(aapi_client, conversation.number, CSV_BYTES, "data.csv")
    fake_bkrepo.fail_signing = True
    token = mint_state_token(conversation.id, epoch=conversation.state_epoch)

    meta = await aapi_client.get(
        build_internal_url(conversation, f"{body['id']}/"), headers={"Authorization": f"Bearer {token}"}
    )

    assert json.loads(meta.content)["code"] == "ATTACHMENT_STORAGE_UNAVAILABLE"
