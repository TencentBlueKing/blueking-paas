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

from pathlib import Path
from unittest import mock

import pytest

from paasng.platform.agent_sandbox.exceptions import ImageBuildSourceError
from paasng.platform.agent_sandbox.image_build.source_prepare import (
    patch_dockerfile,
    prepare_source,
)
from paasng.platform.agent_sandbox.models import ImageBuildRecord

pytestmark = pytest.mark.django_db(databases=["default"])


def _make_source_dir(base: Path, files: dict[str, str]) -> Path:
    """Helper: create a source directory with given {relative_path: content} entries."""
    src_dir = base / "source_root"
    src_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        p = src_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return src_dir


class TestPatchDockerfile:
    def test_inserts_copy_after_from(self, tmp_path: Path):
        """COPY instruction should be inserted right after the FROM line."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11\nRUN pip install flask\n")

        patch_dockerfile(tmp_path, "Dockerfile")

        lines = dockerfile.read_text().splitlines()
        assert lines[0] == "FROM python:3.11"
        assert lines[1] == "COPY daemon /usr/local/bin/daemon"
        assert lines[2] == "RUN pip install flask"

    def test_skips_if_already_present(self, tmp_path: Path):
        """Should not duplicate the COPY instruction."""
        dockerfile = tmp_path / "Dockerfile"
        original = "FROM python:3.11\nCOPY daemon /usr/local/bin/daemon\n"
        dockerfile.write_text(original)

        patch_dockerfile(tmp_path, "Dockerfile")

        assert dockerfile.read_text() == original

    def test_raises_if_no_dockerfile(self, tmp_path: Path):
        """Should raise ImageBuildSourceError when Dockerfile doesn't exist."""
        with pytest.raises(ImageBuildSourceError, match="Dockerfile not found"):
            patch_dockerfile(tmp_path, "Dockerfile")

    def test_raises_if_multi_stage(self, tmp_path: Path):
        """Should raise ImageBuildSourceError for multi-stage builds."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            "FROM golang:1.21 AS builder\nRUN go build\nFROM alpine:3.18\nCOPY --from=builder /app /app\n"
        )

        with pytest.raises(ImageBuildSourceError, match="Multi-stage builds are not supported"):
            patch_dockerfile(tmp_path, "Dockerfile")

    def test_raises_if_no_from(self, tmp_path: Path):
        """Should raise ImageBuildSourceError when Dockerfile has no FROM instruction."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("RUN echo hello\n")

        with pytest.raises(ImageBuildSourceError, match="no FROM instruction found"):
            patch_dockerfile(tmp_path, "Dockerfile")


class TestPrepareSource:
    def test_full_flow(self, build: ImageBuildRecord, tmp_path: Path):
        """The full prepare_source flow: download, inject daemon, patch, upload."""
        source_root = _make_source_dir(tmp_path, {"Dockerfile": "FROM python:3.11\n", "app.py": "print('hi')"})

        # Capture the source directory state when _pack_and_upload is called
        captured_state: dict = {}
        fake_upload_key = f"{build.app_code}/{build.image_name}/prepared.tar.gz"

        def _fake_pack_and_upload(_source_root, _work_dir, _build):
            """Snapshot the prepared source directory and return a fake key."""
            captured_state["files"] = sorted(p.name for p in _source_root.iterdir())
            captured_state["dockerfile"] = (_source_root / "Dockerfile").read_text()
            captured_state["daemon_exists"] = (_source_root / "daemon").exists()
            return fake_upload_key

        _module = "paasng.platform.agent_sandbox.image_build.source_prepare"
        with (
            mock.patch(f"{_module}._download_and_extract", return_value=source_root),
            mock.patch(
                f"{_module}.download_file_from_blob_store",
                side_effect=lambda bucket, key, local_path: Path(local_path).write_bytes(b"fake-daemon-binary"),
            ),
            mock.patch(f"{_module}._pack_and_upload", side_effect=_fake_pack_and_upload),
        ):
            prepare_source(build)

        # -- Verify intermediate state: source directory before re-packing --

        # Daemon binary should be injected
        assert captured_state["daemon_exists"] is True

        # All expected files should be present
        assert "Dockerfile" in captured_state["files"]
        assert "app.py" in captured_state["files"]
        assert "daemon" in captured_state["files"]

        # Dockerfile should contain the COPY instruction for the daemon binary
        assert "COPY daemon /usr/local/bin/daemon" in captured_state["dockerfile"]

        # -- Verify final result --
        build.refresh_from_db()
        assert build.prepared_source_path == fake_upload_key
