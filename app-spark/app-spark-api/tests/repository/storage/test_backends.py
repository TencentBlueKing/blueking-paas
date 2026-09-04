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

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app_spark_api.repository.storage.backends import SourceStorage, make_storage_backend
from app_spark_api.repository.storage.blob_stores import BkRepo, HostTmpPath
from app_spark_api.repository.storage.constants import StorageBackend
from app_spark_api.repository.storage.exceptions import StorageConfigurationError

if TYPE_CHECKING:
    from pathlib import Path


def host_source_storage(package_path: Path) -> SourceStorage:
    """Return source storage keeping its package at a host path."""
    return SourceStorage(HostTmpPath(package_path))


def write_source(source_dir: Path, files: dict[str, bytes]) -> None:
    for relative_path, content in files.items():
        path = source_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def assert_source_files(source_dir: Path, files: dict[str, bytes]) -> None:
    actual_files = {
        str(path.relative_to(source_dir)): path.read_bytes() for path in source_dir.rglob("*") if path.is_file()
    }
    assert actual_files == files


def test_host_tmp_path_store_and_get(tmp_path):
    source_dir = tmp_path / "source"
    expected_files = {
        ".gitignore": b"*.pyc\n",
        "README.md": b"# app-spark\n",
        "src/main.py": b"print('hello')\n",
        "static/logo.bin": b"\x00\x01\xff",
    }
    vcs_metadata = {
        ".git/config": b"git metadata",
        ".hg/hgrc": b"mercurial metadata",
        ".svn/entries": b"subversion metadata",
        ".bzr/branch-format": b"bazaar metadata",
        "CVS/Root": b"cvs metadata",
    }
    write_source(source_dir, expected_files | vcs_metadata)

    package_path = tmp_path / "storage" / "source.tgz"
    storage = host_source_storage(package_path)
    storage.store(source_dir)

    assert package_path.read_bytes().startswith(b"\x1f\x8b")
    target_dir = storage.get(tmp_path / "target")
    assert_source_files(target_dir, expected_files)


def test_host_tmp_path_store_replaces_previous_snapshot(tmp_path):
    source_dir = tmp_path / "source"
    write_source(source_dir, {"keep.txt": b"old", "removed.txt": b"removed"})
    storage = host_source_storage(tmp_path / "source.tgz")
    storage.store(source_dir)

    (source_dir / "keep.txt").write_bytes(b"new")
    (source_dir / "removed.txt").unlink()
    write_source(source_dir, {"added.txt": b"added"})
    storage.store(source_dir)

    assert_source_files(
        storage.get(tmp_path / "target"),
        {"keep.txt": b"new", "added.txt": b"added"},
    )


def test_host_tmp_path_can_store_modified_working_copy(tmp_path):
    source_dir = tmp_path / "source"
    write_source(source_dir, {"main.py": b"before\n"})
    storage = host_source_storage(tmp_path / "source.tgz")
    storage.store(source_dir)

    working_dir = storage.get(tmp_path / "working")
    (working_dir / "main.py").write_bytes(b"after\n")
    storage.store(working_dir)

    assert_source_files(storage.get(tmp_path / "result"), {"main.py": b"after\n"})


def test_store_rejects_missing_source_directory(tmp_path):
    storage = host_source_storage(tmp_path / "source.tgz")

    with pytest.raises(NotADirectoryError, match="Source directory does not exist"):
        storage.store(tmp_path / "missing")


@pytest.mark.parametrize("target_kind", ["file", "non-empty-directory"])
def test_get_rejects_invalid_target(tmp_path, target_kind):
    source_dir = tmp_path / "source"
    write_source(source_dir, {"main.py": b"content\n"})
    storage = host_source_storage(tmp_path / "source.tgz")
    storage.store(source_dir)

    target_path = tmp_path / "target"
    if target_kind == "file":
        target_path.write_text("content")
        expected_exception = NotADirectoryError
    else:
        write_source(target_path, {"existing.txt": b"content"})
        expected_exception = ValueError

    with pytest.raises(expected_exception):
        storage.get(target_path)


@pytest.mark.parametrize(
    ("backend", "config", "expected_type", "error_message"),
    [
        pytest.param(
            StorageBackend.HOST_TMP_PATH,
            {"path": "/tmp/source.tgz"},
            HostTmpPath,
            None,
            id="host-tmp-path-success",
        ),
        pytest.param(
            StorageBackend.HOST_TMP_PATH,
            {"path": ""},
            None,
            "Invalid HostTmpPathConfig",
            id="host-tmp-path-invalid-config",
        ),
        pytest.param(
            StorageBackend.BK_REPO,
            {"bucket": "project-source", "key": "projects/demo/source.tgz"},
            BkRepo,
            None,
            id="bkrepo-success",
        ),
        pytest.param(
            StorageBackend.BK_REPO,
            {"bucket": "project-source"},
            None,
            "Invalid BkRepoConfig",
            id="bkrepo-invalid-config",
        ),
    ],
)
def test_make_storage_backend(settings, backend, config, expected_type, error_message):
    settings.BLOBSTORE_BKREPO_CONFIG = {
        "PROJECT": "bkpaas",
        "ENDPOINT": "https://bkrepo.example.com",
        "USERNAME": "username",
        "PASSWORD": "password",
    }

    if error_message:
        with pytest.raises(StorageConfigurationError, match=error_message):
            make_storage_backend(backend, config)
    else:
        storage = make_storage_backend(backend, config)
        # The configuration only ever selects where the package goes; the tgz half above it is
        # the same object either way.
        assert isinstance(storage, SourceStorage)
        assert isinstance(storage.blob_store, expected_type)
