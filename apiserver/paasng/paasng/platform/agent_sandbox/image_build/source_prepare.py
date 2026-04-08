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

"""Source preparation for image builds.

Downloads the user-provided source tarball, injects the daemon binary,
modifies the Dockerfile to COPY the binary, re-packs and uploads to blobstore.
"""

import logging
import os
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import DAEMON_BINARY_PATH
from paasng.platform.agent_sandbox.exceptions import ImageBuildSourceError
from paasng.platform.sourcectl.package.downloader import download_file_via_url
from paasng.platform.sourcectl.utils import (
    compress_directory,
    find_content_root,
    generate_temp_dir,
    uncompress_directory,
)
from paasng.utils.blobstore import download_file_from_blob_store, make_blob_store

if TYPE_CHECKING:
    from paasng.platform.agent_sandbox.models import ImageBuildRecord

logger = logging.getLogger(__name__)

DAEMON_BINARY_FILENAME = PurePosixPath(DAEMON_BINARY_PATH).name


def prepare_source(build: "ImageBuildRecord"):
    """对用户源码进行预处理，注入 daemon 二进制并修改 Dockerfile，然后重新打包上传。

    Agent sandbox 容器需要一个 daemon 进程来接收和执行指令，但用户提供的镜像
    不会自带该组件。因此在构建前需要将平台侧的 daemon 二进制注入到源码中，并在
    Dockerfile 里添加 COPY 指令，使最终构建出的镜像内置 daemon。

    处理完成后 ``build.prepared_source_path`` 会被更新为上传后的对象 key。
    """
    with generate_temp_dir(suffix="-sbx-img-build") as work_dir:
        # Step 1: Download and extract the source tarball
        source_root = _download_and_extract(build.source_url, work_dir)

        # Step 2: Inject daemon binary and patch Dockerfile
        _inject_daemon_binary(source_root, build.dockerfile_path)

        # Step 3: Re-pack and upload prepared source
        upload_key = _pack_and_upload(source_root, work_dir, build)

        build.prepared_source_path = upload_key
        build.save(update_fields=["prepared_source_path", "updated"])


def patch_dockerfile(source_root: Path, dockerfile_path: str):
    """Insert a COPY instruction for the daemon binary right after the FROM line.
    TODO: 寻找更好的方式来实现这个功能，比如使用 Dockerfile 的模板引擎等。
    """
    dockerfile = source_root / dockerfile_path
    if not dockerfile.exists():
        raise ImageBuildSourceError(f"Dockerfile not found at {dockerfile_path}")

    content = dockerfile.read_text()

    from_matches = re.findall(r"^FROM\s+", content, flags=re.MULTILINE)
    if not from_matches:
        raise ImageBuildSourceError(f"Invalid Dockerfile: no FROM instruction found in {dockerfile_path}")
    if len(from_matches) > 1:
        raise ImageBuildSourceError(
            f"Multi-stage builds are not supported: {len(from_matches)} FROM instructions found in {dockerfile_path}"
        )

    copy_instruction = f"COPY {DAEMON_BINARY_FILENAME} {DAEMON_BINARY_PATH}"

    if copy_instruction in content:
        logger.info("Dockerfile already contains daemon COPY instruction, skipping")
        return

    # 紧接着 FROM 后，是遵照 Dockerfile 的实践，将"不变"的层尽量放前面
    patched = re.sub(
        r"(^FROM\s+.+)$",
        rf"\1\n{copy_instruction}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    dockerfile.write_text(patched)


def _download_and_extract(source_url: str, work_dir: Path) -> Path:
    """Download the source tarball and extract it, returning the source root."""
    tarball_path = work_dir / "source.tar.gz"
    extract_dir = work_dir / "source"
    extract_dir.mkdir()

    download_file_via_url(source_url, tarball_path)
    uncompress_directory(str(tarball_path), str(extract_dir))

    return find_content_root(extract_dir)


def _inject_daemon_binary(source_root: Path, dockerfile_path: str):
    """Download the daemon binary into source_root and patch the Dockerfile."""
    daemon_dest = source_root / DAEMON_BINARY_FILENAME
    download_file_from_blob_store(
        bucket=settings.AGENT_SANDBOX_DAEMON_BUCKET,
        key=settings.AGENT_SANDBOX_DAEMON_KEY,
        local_path=daemon_dest,
    )
    os.chmod(daemon_dest, 0o755)  # noqa: S103

    patch_dockerfile(source_root, dockerfile_path)


def _pack_and_upload(source_root: Path, work_dir: Path, build: "ImageBuildRecord") -> str:
    """Compress the prepared source directory and upload to blobstore, return the object key."""
    tarball_name = "prepared.tar.gz"
    tarball = work_dir / tarball_name
    compress_directory(str(source_root), str(tarball))

    bucket = settings.AGENT_SANDBOX_PACKAGE_BUCKET
    store = make_blob_store(bucket)
    key = f"{build.app_code}/{build.image_name}/{tarball_name}"
    store.upload_file(filepath=tarball, key=key, allow_overwrite=True)
    return key
