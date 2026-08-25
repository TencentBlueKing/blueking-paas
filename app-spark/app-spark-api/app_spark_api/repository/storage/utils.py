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

"""Archive helpers copied from paasng.platform.sourcectl.utils."""

import logging
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

VCS_DIRECTORIES = (".git", ".hg", ".svn", ".bzr", "CVS")


def compress_directory(source_path, target_path):
    """Compress a directory using tar command, excluding VCS metadata."""
    # Use tar command to compress
    # Add "GZIP=-n" to disable gzip timestamp
    # see: https://serverfault.com/questions/110208/different-md5sums-for-same-tar-contents
    process = subprocess.Popen(
        [
            "/bin/tar",
            *(f"--exclude={directory}" for directory in VCS_DIRECTORIES),
            "-czf",
            str(target_path),
            "-C",
            str(source_path),
            ".",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"GZIP": "-n"},
        encoding="utf-8",
    )
    _, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError("Unable to package source, error: %s" % stderr)


def uncompress_directory(source_path, target_path):
    """Uncompress a tar file using tar command."""
    source_path = os.path.abspath(source_path)
    target_path = os.path.abspath(target_path)
    # -m, --touch                don't extract file modified time
    process = subprocess.Popen(
        ["/bin/tar", "-m", "-xf", str(source_path), "-C", str(target_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    _, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError("Unable to unpackage source, error: %s" % stderr)


@contextmanager
def generate_temp_file(suffix="") -> Generator[Path]:
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as file:
        path = Path(file.name)
        logger.debug("Generating temp path: %s", path)
        yield path
