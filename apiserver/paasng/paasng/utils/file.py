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
"""file and path related utilities."""

import os
from pathlib import Path

from paasng.utils.text import generate_random_string


def path_may_escape(input_path: str) -> bool:
    """Check if the input path may escape from a given root directory, an invalid value is like
    "../../../../app_desc.yaml" which can go outside the root directory. This function only perform
    a string-based check and does not resolve symlinks.

    :param input_path: The path to check.
    """
    # Absolute paths are always considered as escaping
    if os.path.isabs(input_path):
        return True
    sim_root = f"/var/folders/{generate_random_string(12)}/T"
    return os.path.commonpath([os.path.abspath(os.path.join(sim_root, input_path)), sim_root]) != sim_root


def validate_source_dir_str(root_path: Path, source_dir_str: str) -> Path:
    """Validate the source_dir string and return the source directory of the module.

    :param root_path: The repository's root directory.
    :param source_dir_str: The source directory string defined by the user.
    :raise ValueError: If the source directory is invalid.
    :return: The source directory.
    """
    source_dir = Path(source_dir_str)
    # If the user configured "/src", change it into "src"
    if source_dir.is_absolute():
        source_dir = Path(source_dir).relative_to("/")

    # Check if the source_dir is valid, resolve the symlink and ensure it is within the root directory
    source_dir = root_path / source_dir
    if not source_dir.resolve().is_relative_to(root_path):
        raise ValueError(f"Invalid source directory: {source_dir_str}")

    if not source_dir.exists():
        raise ValueError(f"The source directory '{source_dir_str}' does not exist")
    if source_dir.is_file():
        raise ValueError(f"The source directory '{source_dir_str}' is not a directory")
    return source_dir
