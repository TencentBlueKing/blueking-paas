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

"""附件里随存储后端而变的部分：新附件写到哪，Runtime 从哪下载。

每种后端一个实现，按名字在 ATTACHMENT_STORAGES 里查。字节本身的读写删仍由 BlobStore 负责，
这里只决定位置和下载方式，调用方不按后端分支。
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

import attrs
from blue_krill.storages.blobstore.bkrepo import RequestError
from django.conf import settings

from app_spark_api.agent.conversations.exceptions import AttachmentStorageError
from app_spark_api.repository.storage.blob_stores import BkRepo
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.entities import BkRepoConfig, structure_storage_config
from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils import structure_config, validate_non_empty_string

if TYPE_CHECKING:
    from uuid import UUID

    from app_spark_api.agent.conversations.models import ConversationAttachment

BK_REPO_KEY_PREFIX = "attachments"

# Runtime 经本服务取附件内容的地址，相对它手里的会话级 state 根。内部路由也由它拼出，两边不会漂移。
AGENT_CONTENT_PATH = "attachments/{attachment_id}/content"

# 预签名下载地址的有效期。Runtime 拿到就立即下载，短一些，泄露了也很快作废。
PRESIGNED_URL_EXPIRES_IN = 300


@attrs.frozen
class AttachmentStorageConfig:
    """Deployment-wide description of where new attachments are written.

    :param backend: A value from StorageBackend.
    :param root: The parent directory for host_tmp_path, the generic repository name for bk_repo.
    """

    backend: str = attrs.field(validator=validate_non_empty_string)
    root: str = attrs.field(validator=validate_non_empty_string)


@attrs.frozen
class AgentDownload:
    """Where the Runtime downloads one attachment from.

    :param url: Absolute, or relative to the Runtime's conversation-scoped state root.
    :param authenticated: Whether the Runtime must send its token. A presigned URL carries its
        own authorization, and sending the token along would hand it to the storage service.
    """

    url: str
    authenticated: bool


class AttachmentStorage(abc.ABC):
    """The backend-specific half of attachment handling."""

    @abc.abstractmethod
    def locate(self, root: str, conversation_id: UUID, attachment_id: UUID, extension: str) -> dict[str, str]:
        """Return the blob-store configuration a new attachment is written to.

        :param root: The configured root, see AttachmentStorageConfig.
        :param extension: Normalized extension including the dot, or "" when there is none.
        """

    @abc.abstractmethod
    def build_agent_download(self, attachment: ConversationAttachment) -> AgentDownload:
        """Return where the Runtime downloads this attachment from.

        :raises AttachmentStorageError: If the storage service could not issue a download.
        """


class HostTmpPathAttachmentStorage(AttachmentStorage):
    """Attachments on this host's disk, which only this service can read."""

    def locate(self, root: str, conversation_id: UUID, attachment_id: UUID, extension: str) -> dict[str, str]:
        """Return a path under root, one directory per conversation."""
        return {"path": f"{root.rstrip('/')}/{conversation_id}/{attachment_id}{extension}"}

    def build_agent_download(self, attachment: ConversationAttachment) -> AgentDownload:
        """Return this service's internal content endpoint."""
        # 文件只在本机磁盘上，没有第三方能替它签地址，只能经本服务转出去。
        return AgentDownload(url=AGENT_CONTENT_PATH.format(attachment_id=attachment.id), authenticated=True)


class BkRepoAttachmentStorage(AttachmentStorage):
    """Attachments in a BkRepo generic repository, downloaded directly by the Runtime."""

    def locate(self, root: str, conversation_id: UUID, attachment_id: UUID, extension: str) -> dict[str, str]:
        """Return a key in the root repository that keeps the original extension."""
        return {"bucket": root, "key": f"{BK_REPO_KEY_PREFIX}/{conversation_id}/{attachment_id}{extension}"}

    def build_agent_download(self, attachment: ConversationAttachment) -> AgentDownload:
        """Return a short-lived presigned URL, so the bytes do not pass through this service."""
        config = structure_storage_config(attachment.config, BkRepoConfig)
        try:
            url = BkRepo(bucket=config.bucket, key=config.key).generate_presigned_url(PRESIGNED_URL_EXPIRES_IN)
        # requests 自己的失败（连不上、超时）是 OSError 的子类，blue_krill 不会包装它们。
        except (RequestError, OSError) as exc:
            raise AttachmentStorageError(f"Could not sign a download URL for attachment {attachment.id}") from exc

        return AgentDownload(url=url, authenticated=False)


ATTACHMENT_STORAGES: dict[StorageBackend, AttachmentStorage] = {
    StorageBackend.HOST_TMP_PATH: HostTmpPathAttachmentStorage(),
    StorageBackend.BK_REPO: BkRepoAttachmentStorage(),
}


def get_attachment_storage_config() -> AttachmentStorageConfig:
    """Return the configured location for new attachments.

    :raises StorageConfigurationError: If AGENT_ATTACHMENT_STORAGE is invalid.
    """
    return structure_config(
        settings.AGENT_ATTACHMENT_STORAGE, AttachmentStorageConfig, error_cls=StorageConfigurationError
    )


def resolve_attachment_storage(backend: str) -> AttachmentStorage:
    """Return the implementation for a backend name, from settings or from an attachment row.

    :raises StorageConfigurationError: If no implementation handles the backend.
    """
    try:
        return ATTACHMENT_STORAGES[StorageBackend(backend)]
    except (ValueError, KeyError) as exc:
        raise StorageConfigurationError(f"Unsupported attachment storage backend: {backend}") from exc
