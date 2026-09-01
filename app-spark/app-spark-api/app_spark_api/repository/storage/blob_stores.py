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

"""One named place a single blob is kept, and the engines that can be that place.

Extracted from the source-package storage above it because two unrelated things turned out to
need the same primitive: a Project's source snapshot, which is a tgz of a directory, and a
conversation's context document, which is a few megabytes of JSON. Only the first has anything
to do with directories or compression, so that part stays in
:mod:`~app_spark_api.repository.storage.backends` and this layer transfers bytes.

A store addresses exactly one blob: where it sits is settled when the store is built, so
nothing above has to carry a key around.
"""

from __future__ import annotations

import abc
import io
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from blue_krill.storages.blobstore.bkrepo import BKGenericRepo
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.entities import (
    BkRepoConfig,
    HostTmpPathConfig,
    structure_storage_config,
)
from app_spark_api.repository.storage.exceptions import StorageConfigurationError

if TYPE_CHECKING:
    from os import PathLike

    StrPath = str | PathLike[str]


class BlobStore(abc.ABC):
    """Read and replace the one blob this store addresses.

    Implementations provide only the streaming pair. Everything else is derived here, and the
    two derivations exist for genuinely different callers: a source package is a file on disk
    that may be large, so it must stream, while a context document is produced and consumed in
    memory and would gain nothing from a detour through a temporary file.
    """

    @abc.abstractmethod
    def upload(self, handle: BinaryIO) -> None:
        """Replace the blob with everything readable from ``handle``.

        :param handle: Readable binary stream positioned at the start of the content.
        """

    @abc.abstractmethod
    def download(self, handle: BinaryIO) -> None:
        """Write the blob into ``handle``.

        :param handle: Writable binary stream.
        """

    def put(self, path: StrPath) -> None:
        """Replace the blob with the contents of a local file.

        :param path: Existing local file to upload.
        """
        with Path(path).open("rb") as handle:
            self.upload(handle)

    def fetch(self, path: StrPath) -> None:
        """Write the blob to a local file, replacing it if it exists.

        :param path: Local path to write to; its parent must exist.
        """
        with Path(path).open("wb") as handle:
            self.download(handle)

    def put_bytes(self, data: bytes) -> None:
        """Replace the blob with ``data``.

        :param data: New content.
        """
        self.upload(io.BytesIO(data))

    def get_bytes(self) -> bytes:
        """Return the blob's current content.

        :return: The stored bytes.
        """
        buffer = io.BytesIO()
        self.download(buffer)
        return buffer.getvalue()


class HostTmpPath(BlobStore):
    """Keep a blob at a path on the current host.

    :param path: Host path the blob is persisted at.
    """

    def __init__(self, path: StrPath):
        self.path = Path(path)

    def upload(self, handle: BinaryIO) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            # Write beside the destination so os.replace remains atomic on one filesystem.
            with tempfile.NamedTemporaryFile(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                shutil.copyfileobj(handle, temporary_file)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def download(self, handle: BinaryIO) -> None:
        with self.path.open("rb") as stored:
            shutil.copyfileobj(stored, handle)


class BkRepo(BlobStore):
    """Keep a blob in a BlueKing generic artifact repository.

    :param bucket: Name of the BkRepo generic repository.
    :param key: Object key the blob is stored under.
    """

    def __init__(self, bucket: str, key: str):
        self.key = key
        config = settings.BLOBSTORE_BKREPO_CONFIG
        if not isinstance(config, Mapping):
            raise ImproperlyConfigured("BLOBSTORE_BKREPO_CONFIG must be configured for the BkRepo backend")

        required_settings = {"PROJECT", "ENDPOINT", "USERNAME", "PASSWORD"}
        if missing := required_settings - config.keys():
            fields = ", ".join(sorted(missing))
            raise ImproperlyConfigured(f"BLOBSTORE_BKREPO_CONFIG is missing fields: {fields}")

        self.client = BKGenericRepo(
            bucket=bucket,
            project=config["PROJECT"],
            endpoint_url=config["ENDPOINT"],
            username=config["USERNAME"],
            password=config["PASSWORD"],
        )

    def upload(self, handle: BinaryIO) -> None:
        self.client.upload_fileobj(handle, self.key, allow_overwrite=True)

    def download(self, handle: BinaryIO) -> None:
        self.client.download_fileobj(key=self.key, fh=handle)


def make_blob_store(backend: str, config: object) -> BlobStore:
    """Build the blob store a persisted backend name and configuration describe.

    Example::

        store = make_blob_store(
            StorageBackend.HOST_TMP_PATH,
            {"path": "/tmp/app-spark/conversation-context.json"},
        )
        store.put_bytes(b'{"schema_version": 3}')

    :param backend: A value from :class:`~app_spark_api.repository.storage.constants.
        StorageBackend` identifying the storage engine.
    :param config: Backend-specific configuration mapping. HostTmpPath requires ``path``;
        BkRepo requires ``bucket`` and ``key``.
    :return: A validated blob store.
    :raises StorageConfigurationError: If the backend is unknown or the configuration cannot be
        structured into the corresponding attrs model.
    """
    try:
        storage_backend = StorageBackend(backend)
    except ValueError as exc:
        raise StorageConfigurationError(f"Unknown storage backend: {backend}") from exc

    if storage_backend == StorageBackend.HOST_TMP_PATH:
        host_config = structure_storage_config(config, HostTmpPathConfig)
        return HostTmpPath(path=host_config.path)

    if storage_backend == StorageBackend.BK_REPO:
        bkrepo_config = structure_storage_config(config, BkRepoConfig)
        return BkRepo(bucket=bkrepo_config.bucket, key=bkrepo_config.key)

    raise StorageConfigurationError(f"Unsupported storage backend: {storage_backend}")
