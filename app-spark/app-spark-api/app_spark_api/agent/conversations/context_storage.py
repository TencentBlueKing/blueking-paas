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

"""Deciding where one conversation's context document goes.

Two things are deliberately kept apart. The deployment says *which* storage engine and under
*what* root, once, in settings. This module turns that plus a conversation id into the concrete
per-conversation configuration -- which is then recorded on the snapshot row, so a later change
to the setting cannot orphan a document already written under the old one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
from django.conf import settings

from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.exceptions import StorageConfigurationError
from app_spark_api.utils import structure_config, validate_non_empty_string

if TYPE_CHECKING:
    from uuid import UUID

# Fixed rather than configurable: it only has to keep conversation documents from colliding
# with anything else in the same bucket, and a knob here would be one more thing that can be
# set to a value the already-written keys do not use.
BK_REPO_KEY_PREFIX = "conversations"

CONTEXT_DOCUMENT_NAME = "context.json"


@attrs.frozen
class ContextStorageConfig:
    """Deployment-wide description of where conversation contexts are archived.

    :param backend: A value from :class:`~app_spark_api.repository.storage.constants.
        StorageBackend`.
    :param root: What ``backend`` needs to be pointed at: the parent directory for
        ``host_tmp_path``, the generic repository name for ``bk_repo``.
    """

    backend: str = attrs.field(validator=validate_non_empty_string)
    root: str = attrs.field(validator=validate_non_empty_string)


def get_context_storage_config() -> ContextStorageConfig:
    """Return the configured archive location for conversation contexts.

    :return: A validated configuration.
    :raises StorageConfigurationError: If the setting has missing, extra, or invalid fields.
    """
    return structure_config(
        settings.AGENT_CONTEXT_STORAGE,
        ContextStorageConfig,
        error_cls=StorageConfigurationError,
    )


def blob_location(conversation_id: UUID) -> tuple[str, dict[str, str]]:
    """Return the backend name and blob-store configuration for one conversation's context.

    Example::

        backend, config = blob_location(conversation.id)
        snapshot = ConversationContextSnapshot(backend=backend, config=config, ...)

    :param conversation_id: Conversation whose context document is being addressed.
    :return: The backend name and the configuration
        :func:`~app_spark_api.repository.storage.blob_stores.make_blob_store` expects.
    :raises StorageConfigurationError: If the configured backend is unknown.
    """
    config = get_context_storage_config()
    try:
        backend = StorageBackend(config.backend)
    except ValueError as exc:
        raise StorageConfigurationError(f"Unknown storage backend: {config.backend}") from exc

    if backend == StorageBackend.HOST_TMP_PATH:
        return backend.value, {"path": f"{config.root.rstrip('/')}/{conversation_id}.json"}

    if backend == StorageBackend.BK_REPO:
        return backend.value, {
            "bucket": config.root,
            "key": f"{BK_REPO_KEY_PREFIX}/{conversation_id}/{CONTEXT_DOCUMENT_NAME}",
        }

    raise StorageConfigurationError(f"Unsupported storage backend: {backend}")
