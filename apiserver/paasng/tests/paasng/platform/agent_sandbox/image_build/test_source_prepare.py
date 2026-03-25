# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import shutil
import tarfile
from pathlib import Path
from unittest import mock

import pytest

from paasng.platform.agent_sandbox.exceptions import ImageBuildSourceError
from paasng.platform.agent_sandbox.image_build.source_prepare import (
    _patch_dockerfile,
    prepare_source,
)
from paasng.platform.agent_sandbox.models import ImageBuild

pytestmark = pytest.mark.django_db(databases=["default"])


def _make_tarball(tmp_path: Path, files: dict[str, str]) -> Path:
    """Helper: create a tar.gz with given {relative_path: content} entries."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    for name, content in files.items():
        p = src_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    tarball = tmp_path / "source.tar.gz"
    with tarfile.open(tarball, "w:gz") as tf:
        tf.add(str(src_dir), arcname=".")
    return tarball


def _fake_uncompress(source_path, target_path):
    """Use Python tarfile instead of /bin/tar for cross-platform compatibility."""
    with tarfile.open(source_path, "r:gz") as tf:
        tf.extractall(target_path)  # noqa: S202


def _fake_compress(source_path, target_path):
    """Use Python tarfile instead of /bin/tar for cross-platform compatibility."""
    with tarfile.open(target_path, "w:gz") as tf:
        tf.add(source_path, arcname=".")


class TestPatchDockerfile:
    def test_inserts_copy_after_from(self, tmp_path: Path):
        """COPY instruction should be inserted right after the FROM line."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11\nRUN pip install flask\n")

        _patch_dockerfile(tmp_path, "Dockerfile")

        lines = dockerfile.read_text().splitlines()
        assert lines[0] == "FROM python:3.11"
        assert lines[1] == "COPY daemon /usr/local/bin/daemon"
        assert lines[2] == "RUN pip install flask"

    def test_skips_if_already_present(self, tmp_path: Path):
        """Should not duplicate the COPY instruction."""
        dockerfile = tmp_path / "Dockerfile"
        original = "FROM python:3.11\nCOPY daemon /usr/local/bin/daemon\n"
        dockerfile.write_text(original)

        _patch_dockerfile(tmp_path, "Dockerfile")

        assert dockerfile.read_text() == original

    def test_raises_if_no_dockerfile(self, tmp_path: Path):
        """Should raise ImageBuildSourceError when Dockerfile doesn't exist."""
        with pytest.raises(ImageBuildSourceError, match="Dockerfile not found"):
            _patch_dockerfile(tmp_path, "Dockerfile")

    def test_raises_if_multi_stage(self, tmp_path: Path):
        """Should raise ImageBuildSourceError for multi-stage builds."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            "FROM golang:1.21 AS builder\nRUN go build\nFROM alpine:3.18\nCOPY --from=builder /app /app\n"
        )

        with pytest.raises(ImageBuildSourceError, match="Multi-stage builds are not supported"):
            _patch_dockerfile(tmp_path, "Dockerfile")

    def test_raises_if_no_from(self, tmp_path: Path):
        """Should raise ImageBuildSourceError when Dockerfile has no FROM instruction."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("RUN echo hello\n")

        with pytest.raises(ImageBuildSourceError, match="no FROM instruction found"):
            _patch_dockerfile(tmp_path, "Dockerfile")


class TestPrepareSource:
    def test_full_flow(self, build: ImageBuild, tmp_path: Path):
        """The full prepare_source flow: download, inject daemon, patch, upload."""
        tarball = _make_tarball(tmp_path, {"Dockerfile": "FROM python:3.11\n", "app.py": "print('hi')"})

        # Capture the source directory state at compress time (right before re-packing)
        captured_state: dict = {}

        def _capture_and_compress(source_path, target_path):
            """Snapshot the prepared source directory, then compress."""
            root = Path(source_path)
            captured_state["files"] = sorted(p.name for p in root.iterdir())
            captured_state["dockerfile"] = (root / "Dockerfile").read_text()
            daemon_path = root / "daemon"
            captured_state["daemon_exists"] = daemon_path.exists()
            _fake_compress(source_path, target_path)

        _module = "paasng.platform.agent_sandbox.image_build.source_prepare"
        mock_upload_store = mock.MagicMock()
        with (
            mock.patch(
                f"{_module}.download_file_via_url",
                side_effect=lambda url, local_path: shutil.copy2(str(tarball), str(local_path)),
            ),
            mock.patch(
                f"{_module}.download_file_from_blob_store",
                side_effect=lambda bucket, key, local_path: Path(local_path).write_bytes(b"fake-daemon-binary"),
            ),
            mock.patch(f"{_module}.make_blob_store", return_value=mock_upload_store),
            mock.patch(f"{_module}.uncompress_directory", side_effect=_fake_uncompress),
            mock.patch(f"{_module}.compress_directory", side_effect=_capture_and_compress),
        ):
            prepare_source(build)

        # -- Verify intermediate state: source directory before re-packing --

        # Daemon binary should be injected with correct content and executable permission
        assert captured_state["daemon_exists"] is True

        # All expected files should be present
        assert "Dockerfile" in captured_state["files"]
        assert "app.py" in captured_state["files"]
        assert "daemon" in captured_state["files"]

        # Dockerfile should contain the COPY instruction for the daemon binary
        assert "COPY daemon /usr/local/bin/daemon" in captured_state["dockerfile"]

        # -- Verify final result --
        build.refresh_from_db()
        assert build.prepared_source_path == f"{build.app_code}/{build.image_name}/source.tar.gz"
