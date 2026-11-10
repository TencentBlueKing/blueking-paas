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

"""会话图片附件：上传即存、发送时只引用 ID，字节始终经本服务读出。

上下文里只放 app-spark-attachment://<附件 ID>，Agent 调模型前再经内部接口按 ID 取回字节。
前端预览和 Agent 取图都不签发存储链接：沙箱和浏览器能否直连 BkRepo 没有保证。日后要让字节
绕开本服务，把内容接口改成 302 跳转即可，调用方不用改。
"""

from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING, BinaryIO

from asgiref.sync import sync_to_async
from blue_krill.storages.blobstore.bkrepo import RequestError
from django.conf import settings

from app_spark_api.agent.conversations.context_storage import ContextStorageConfig
from app_spark_api.agent.conversations.entities import AttachmentResponse
from app_spark_api.agent.conversations.exceptions import (
    AttachmentAlreadyUsedError,
    AttachmentNotFoundError,
    AttachmentStorageError,
    AttachmentTooLargeError,
    AttachmentTypeUnsupportedError,
    ConversationClosedError,
)
from app_spark_api.agent.conversations.models import ConversationAttachment
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils import structure_config
from app_spark_api.utils.urls import reverse_public

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app_spark_api.agent.conversations.models import Conversation

# 单张附件的大小上限。前端会先压缩到最长边 2048，正常截图远小于它，所以读写都整张放内存。
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
ATTACHMENT_URI_SCHEME = "app-spark-attachment"
BK_REPO_KEY_PREFIX = "attachments"

# 用户侧内容接口的路由名，AttachmentResponse.url 由它反解出来。
ATTACHMENT_CONTENT_URL_NAME = "conversations-attachment-content"


def blob_location(conversation_id: uuid.UUID, attachment_id: uuid.UUID) -> tuple[str, dict[str, str]]:
    """Return the backend name and blob-store configuration for one attachment.

    :raises StorageConfigurationError: If AGENT_ATTACHMENT_STORAGE is invalid.
    """
    # 与上下文存储的配置同构（backend + root），直接复用它的结构。
    config = structure_config(
        settings.AGENT_ATTACHMENT_STORAGE, ContextStorageConfig, error_cls=StorageConfigurationError
    )
    if config.backend == StorageBackend.HOST_TMP_PATH:
        return config.backend, {"path": f"{config.root.rstrip('/')}/{conversation_id}/{attachment_id}"}

    if config.backend == StorageBackend.BK_REPO:
        return config.backend, {
            "bucket": config.root,
            "key": f"{BK_REPO_KEY_PREFIX}/{conversation_id}/{attachment_id}",
        }

    raise StorageConfigurationError(f"Unsupported storage backend: {config.backend}")


def sniff_image_type(head: bytes) -> str | None:
    """Return the image MIME type the leading bytes of a file identify, or None."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"

    # WebP 是 RIFF 容器：前 4 字节 RIFF，中间 4 字节是长度，再 4 字节才是格式名。
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"

    return None


def build_attachment_uri(attachment_id: uuid.UUID) -> str:
    """Return the reference a conversation context uses for one attachment."""
    return f"{ATTACHMENT_URI_SCHEME}://{attachment_id}"


def build_attachment_response(
    attachment: ConversationAttachment, *, project_id: str, number: int
) -> AttachmentResponse:
    """Present an attachment with the path its content is read from."""
    url = reverse_public(
        f"api:{ATTACHMENT_CONTENT_URL_NAME}",
        kwargs={"project_id": project_id, "number": number, "attachment_id": attachment.id},
    )
    return AttachmentResponse(
        id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size=attachment.size,
        url=url,
        created_at=attachment.created_at,
    )


@sync_to_async
def asave_attachment(conversation: Conversation, *, handle: BinaryIO, filename: str) -> ConversationAttachment:
    """Store one uploaded image and record it as an unused attachment of the conversation.

    :raises ConversationClosedError: If the conversation has been closed.
    :raises AttachmentTooLargeError: If the file exceeds MAX_ATTACHMENT_SIZE.
    :raises AttachmentTypeUnsupportedError: If the file is not an allowed image type.
    :raises AttachmentStorageError: If the bytes could not be written.
    """
    # 已结束的会话不会再有下一轮，往里上传的附件永远不会被用上。
    if not conversation.is_live:
        raise ConversationClosedError(f"Conversation {conversation.id} has been closed")

    # 多读一个字节就能判断是否超限，不信任 multipart 头里声明的大小。
    data = handle.read(MAX_ATTACHMENT_SIZE + 1)
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise AttachmentTooLargeError(f"Attachment exceeds {MAX_ATTACHMENT_SIZE} bytes")

    # 按文件头识别类型，不信任客户端声明的 Content-Type 和扩展名。
    mime_type = sniff_image_type(data[:12])
    if mime_type is None:
        raise AttachmentTypeUnsupportedError("The uploaded file is not a PNG, JPEG, GIF or WebP image")

    attachment_id = uuid.uuid4()
    backend, config = blob_location(conversation.id, attachment_id)
    attachment = ConversationAttachment(
        id=attachment_id,
        conversation=conversation,
        filename=filename[:MAX_FILENAME_LENGTH],
        mime_type=mime_type,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        backend=backend,
        config=config,
        tenant_id=conversation.tenant_id,
        owner=conversation.owner,
    )

    # 先写字节再落行：写失败时不能留下一行指向不存在对象的附件。
    try:
        attachment.get_blob_store().put_bytes(data)
    except (RequestError, OSError) as exc:
        raise AttachmentStorageError(f"Could not store attachment {attachment_id}") from exc

    attachment.save(force_insert=True)
    return attachment


async def aget_attachment(conversation: Conversation, attachment_id: uuid.UUID) -> ConversationAttachment:
    """Return one of the conversation's attachments.

    :raises AttachmentNotFoundError: If the conversation has no such attachment.
    """
    try:
        return await ConversationAttachment.objects.aget(conversation=conversation, id=attachment_id)
    except ConversationAttachment.DoesNotExist as exc:
        raise AttachmentNotFoundError(f"Conversation {conversation.id} has no attachment {attachment_id}") from exc


@sync_to_async
def aread_content(attachment: ConversationAttachment) -> bytes:
    """Return an attachment's bytes.

    :raises AttachmentStorageError: If the bytes could not be read.
    """
    try:
        return attachment.get_blob_store().get_bytes()
    except (RequestError, OSError) as exc:
        raise AttachmentStorageError(f"Could not read attachment {attachment.id}") from exc


async def acheck_run_attachments(
    conversation: Conversation, attachment_ids: Sequence[uuid.UUID]
) -> list[ConversationAttachment]:
    """Return the attachments a turn refers to, in order, having checked they can be sent with it.

    Checked before a Runtime is brought up, so a turn that cannot happen costs nothing; the
    binding re-checks under a lock, see ConversationUserMessageManager.

    :raises AttachmentNotFoundError: If one of them is not the conversation's.
    :raises AttachmentAlreadyUsedError: If one of them was already sent with another turn.
    """
    found = {
        attachment.id: attachment
        async for attachment in ConversationAttachment.objects.filter(conversation=conversation, id__in=attachment_ids)
    }
    if missing := [attachment_id for attachment_id in attachment_ids if attachment_id not in found]:
        raise AttachmentNotFoundError(f"Conversation {conversation.id} has no attachments {missing}")

    attachments = [found[attachment_id] for attachment_id in attachment_ids]
    if used := [attachment.id for attachment in attachments if attachment.user_message_id is not None]:
        raise AttachmentAlreadyUsedError(f"Attachments {used} of conversation {conversation.id} are already in use")

    return attachments
