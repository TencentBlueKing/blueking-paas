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

"""Storing a Project's source tree as a single package.

Only the directory-and-tgz half lives here. Where the package actually goes is a
:class:`~app_spark_api.repository.storage.blob_stores.BlobStore`, which knows nothing about
source trees -- and is therefore reusable by the conversation context, which is a blob too.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app_spark_api.repository.storage.blob_stores import BlobStore, make_blob_store
from app_spark_api.repository.storage.utils import compress_directory, generate_temp_file, uncompress_directory

if TYPE_CHECKING:
    from os import PathLike

    StrPath = str | PathLike[str]


class SourceStorage:
    """Storage for the current source snapshot of a Project.

    Owns the directory validation and tgz compression lifecycle; the transfer itself is the
    blob store's business.

    :param blob_store: Where the compressed package is kept.
    """

    def __init__(self, blob_store: BlobStore):
        self.blob_store = blob_store

    def store(self, source_dir: StrPath) -> None:
        """Compress and replace the current source snapshot.

        :param source_dir: Existing source directory to package and persist.
        :raises NotADirectoryError: If ``source_dir`` is not an existing directory.
        """
        source_path = Path(source_dir)
        if not source_path.is_dir():
            raise NotADirectoryError(f"Source directory does not exist: {source_path}")

        with generate_temp_file(suffix=".tgz") as package_path:
            compress_directory(source_path, package_path)
            self.blob_store.put(package_path)

    def get(self, target_dir: StrPath) -> Path:
        """Extract the current source snapshot into an empty directory.

        :param target_dir: Missing or empty directory that will receive the source files.
        :return: The normalized target directory path.
        :raises NotADirectoryError: If ``target_dir`` exists and is not a directory.
        :raises ValueError: If ``target_dir`` is not empty.
        """
        target_path = Path(target_dir)
        if target_path.exists():
            if not target_path.is_dir():
                raise NotADirectoryError(f"Target path is not a directory: {target_path}")
            if any(target_path.iterdir()):
                raise ValueError(f"Target directory must be empty: {target_path}")
        else:
            target_path.mkdir(parents=True)

        with generate_temp_file(suffix=".tgz") as package_path:
            self.blob_store.fetch(package_path)
            uncompress_directory(package_path, target_path)
        return target_path


def make_storage_backend(backend: str, config: object) -> SourceStorage:
    """Build a source storage backend from persisted model configuration.

    Example::

        storage = make_storage_backend(
            StorageBackend.HOST_TMP_PATH,
            {"path": "/tmp/app-spark/project-source.tgz"},
        )
        storage.store("/tmp/app-spark/project-source")

    :param backend: A value from :class:`~app_spark_api.repository.storage.constants.
        StorageBackend` identifying the storage engine.
    :param config: Backend-specific configuration mapping. HostTmpPath requires
        ``path``; BkRepo requires ``bucket`` and ``key``.
    :return: A validated storage backend instance.
    :raises StorageConfigurationError: If the backend is unknown or the configuration
        cannot be structured into the corresponding attrs model.
    """
    return SourceStorage(make_blob_store(backend, config))
