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

"""The single-blob layer under both the source packages and the conversation contexts."""

from __future__ import annotations

import pytest

from app_spark_api.repository.storage.blob_stores import HostTmpPath, make_blob_store
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.exceptions import StorageConfigurationError

CONTEXT_DOCUMENT = b'{"schema_version": 3, "context_version": 7}'


def test_bytes_round_trip_without_touching_a_temporary_file(tmp_path):
    """The in-memory pair is what the conversation context uses, and it has no file to lend."""
    store = HostTmpPath(tmp_path / "nested" / "context.json")

    store.put_bytes(CONTEXT_DOCUMENT)

    assert store.get_bytes() == CONTEXT_DOCUMENT
    assert store.path.read_bytes() == CONTEXT_DOCUMENT


def test_a_blob_is_replaced_whole(tmp_path):
    store = HostTmpPath(tmp_path / "context.json")
    store.put_bytes(b"x" * 4096)

    store.put_bytes(CONTEXT_DOCUMENT)

    assert store.get_bytes() == CONTEXT_DOCUMENT
    # Nothing staged is left behind: a replacement writes a sibling and renames it into place.
    assert [path.name for path in tmp_path.iterdir()] == ["context.json"]


def test_the_file_pair_and_the_bytes_pair_see_the_same_blob(tmp_path):
    store = HostTmpPath(tmp_path / "context.json")
    source = tmp_path / "source.json"
    source.write_bytes(CONTEXT_DOCUMENT)

    store.put(source)

    fetched = tmp_path / "fetched.json"
    store.fetch(fetched)
    assert fetched.read_bytes() == CONTEXT_DOCUMENT
    assert store.get_bytes() == CONTEXT_DOCUMENT


def test_fetching_a_missing_blob_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        HostTmpPath(tmp_path / "absent.json").get_bytes()


def test_make_blob_store_rejects_an_unknown_backend():
    with pytest.raises(StorageConfigurationError, match="Unknown storage backend"):
        make_blob_store("nowhere", {})


def test_make_blob_store_builds_a_host_path_store(tmp_path):
    store = make_blob_store(StorageBackend.HOST_TMP_PATH, {"path": str(tmp_path / "blob")})

    assert isinstance(store, HostTmpPath)
    assert store.path == tmp_path / "blob"
