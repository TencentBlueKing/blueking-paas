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

"""会话文件附件：上传即存、发送时只引用 ID。

上下文里只放 app-spark-attachment://<附件 ID>，Agent 在一轮开始前按 ID 把文件下载进工作区。
前端预览始终经本服务读取，有浏览器缓存兜着；Agent 从哪下载由存储后端决定，见 attachment_storage。
"""

from __future__ import annotations

import functools
import hashlib
import logging
import mimetypes
import re
import uuid
from pathlib import PurePath
from typing import TYPE_CHECKING, BinaryIO

from asgiref.sync import sync_to_async
from blue_krill.storages.blobstore.bkrepo import RequestError
from magika import Magika

from app_spark_api.agent.conversations.attachment_storage import (
    get_attachment_storage_config,
    resolve_attachment_storage,
)
from app_spark_api.agent.conversations.entities import AttachmentResponse
from app_spark_api.agent.conversations.exceptions import AttachmentStorageError, ConversationClosedError
from app_spark_api.agent.conversations.models import ConversationAttachment
from app_spark_api.utils.api_errors.error_codes import error_codes
from app_spark_api.utils.urls import reverse_public

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app_spark_api.agent.conversations.attachment_storage import AgentAttachmentSource
    from app_spark_api.agent.conversations.models import Conversation

logger = logging.getLogger(__name__)

# 单个附件的大小上限。读写都整份放内存，所以不能放得太大。
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
ATTACHMENT_URI_SCHEME = "app-spark-attachment"

# 能作为图片直接交给多模态模型、也能在浏览器里内联显示的类型。SVG 不在其中：它能带脚本。
IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})

# magika 只认出「某种文本」或完全认不出时的标签。这时扩展名往往更具体，例如 Markdown 会被认成 txt。
GENERIC_CONTENT_LABELS = frozenset({"txt", "unknown", "empty"})
FALLBACK_MIME_TYPE = "application/octet-stream"

# 扩展名只收短的字母数字：它会进存储路径，也会拿去猜类型，奇怪的后缀不如没有。
EXTENSION_PATTERN = re.compile(r"\.[a-z0-9]{1,16}")

# 用户侧内容接口的路由名，AttachmentResponse.url 由它反解出来。
ATTACHMENT_CONTENT_URL_NAME = "conversations-attachments-content"


@functools.cache
def get_magika() -> Magika:
    """Return the process-wide content type detector, loading its model on first use."""
    return Magika()


def normalize_extension(filename: str) -> str:
    """Return the file name's extension, lowercased and with its dot, or "" when it has no usable one."""
    suffix = PurePath(filename).suffix.lower()
    if EXTENSION_PATTERN.fullmatch(suffix) is None:
        return ""

    return suffix


def detect_mime_type(data: bytes, extension: str) -> str:
    """Return a file's MIME type, judged by its content first and its extension second."""
    result = get_magika().identify_bytes(data)
    if not result.ok:
        return FALLBACK_MIME_TYPE

    detected = result.output
    guessed = mimetypes.guess_type(f"file{extension}")[0] if extension else None

    # 没有扩展名可比，或两者说的是同一种类型：以内容为准。
    if guessed is None or extension.removeprefix(".") in detected.extensions or guessed == detected.mime_type:
        return detected.mime_type

    # 内容只认出泛泛的文本或认不出时，扩展名更具体。但扩展名不能单独把文件定成图片：
    # 图片会原样作为图片交给模型，伪装成图片的文件只会让模型调用失败。
    if detected.label in GENERIC_CONTENT_LABELS and guessed not in IMAGE_MIME_TYPES:
        return guessed

    logger.info("attachment content looks like %s but its extension %s says %s", detected.label, extension, guessed)
    return detected.mime_type


def is_image(mime_type: str) -> bool:
    """Return whether a model that reads images is handed this type as an image."""
    return mime_type in IMAGE_MIME_TYPES


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
    """Store one uploaded file and record it as an unused attachment of the conversation.

    :raises ConversationClosedError: If the conversation has been closed.
    :raises APIError: ATTACHMENT_TOO_LARGE if the file exceeds MAX_ATTACHMENT_SIZE.
    :raises AttachmentStorageError: If the bytes could not be written.
    :raises StorageConfigurationError: If AGENT_ATTACHMENT_STORAGE is invalid.
    """
    # 已结束的会话不会再有下一轮，往里上传的附件永远不会被用上。
    if not conversation.is_live:
        raise ConversationClosedError(f"Conversation {conversation.id} has been closed")

    # 多读一个字节就能判断是否超限，不信任 multipart 头里声明的大小。
    data = handle.read(MAX_ATTACHMENT_SIZE + 1)
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise error_codes.ATTACHMENT_TOO_LARGE

    extension = normalize_extension(filename)
    attachment_id = uuid.uuid4()
    config = get_attachment_storage_config()
    attachment = ConversationAttachment(
        id=attachment_id,
        conversation=conversation,
        filename=filename[:MAX_FILENAME_LENGTH],
        extension=extension,
        mime_type=detect_mime_type(data, extension),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        backend=config.backend,
        config=resolve_attachment_storage(config.backend).locate(
            config.root, conversation.id, attachment_id, extension
        ),
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

    :raises APIError: ATTACHMENT_NOT_FOUND if the conversation has no such attachment.
    """
    try:
        return await ConversationAttachment.objects.aget(conversation=conversation, id=attachment_id)
    except ConversationAttachment.DoesNotExist as exc:
        raise error_codes.ATTACHMENT_NOT_FOUND from exc


@sync_to_async
def aread_content(attachment: ConversationAttachment) -> bytes:
    """Return an attachment's bytes.

    :raises AttachmentStorageError: If the bytes could not be read.
    """
    try:
        return attachment.get_blob_store().get_bytes()
    except (RequestError, OSError) as exc:
        raise AttachmentStorageError(f"Could not read attachment {attachment.id}") from exc


@sync_to_async
def abuild_agent_attachment_source(attachment: ConversationAttachment) -> AgentAttachmentSource:
    """Return where the Runtime gets an attachment, as its storage backend decides.

    :raises AttachmentStorageError: If the storage service could not issue a download.
    :raises StorageConfigurationError: If the attachment's backend is not supported.
    """
    # 按这一行记下的后端选，而不是按当前配置：部署切换存储之后，老附件仍在原来的地方。
    return resolve_attachment_storage(attachment.backend).build_agent_attachment_source(attachment)


async def acheck_run_attachments(
    conversation: Conversation, attachment_ids: Sequence[uuid.UUID]
) -> list[ConversationAttachment]:
    """Return the attachments a turn refers to, in order, having checked they can be sent with it.

    Checked before a Runtime is brought up, so a turn that cannot happen costs nothing; the
    binding re-checks under a lock, see ConversationUserMessageManager.

    :raises APIError: ATTACHMENT_NOT_FOUND or ATTACHMENT_ALREADY_USED, see select_unsent.
    """
    return await sync_to_async(ConversationAttachment.objects.select_unsent)(conversation, attachment_ids)


async def ahas_sent_images(conversation: Conversation) -> bool:
    """Return whether any earlier turn of the conversation was sent with an image attachment."""
    return await ConversationAttachment.objects.filter(
        conversation=conversation, user_message__isnull=False, mime_type__in=IMAGE_MIME_TYPES
    ).aexists()
