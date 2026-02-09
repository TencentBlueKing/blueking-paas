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
"""File system related operations in agent sandbox"""

from abc import ABC, abstractmethod


class SandboxFS(ABC):
    """The file system operations abstract interface in agent sandbox"""

    @abstractmethod
    def create_folder(self, path: str, mode: str) -> None:
        """Create a new empty folder."""
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, file: bytes, remote_path: str, timeout: int = 30 * 60) -> None:
        """Upload a file to the sandbox."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file or folder from the sandbox."""
        raise NotImplementedError

    @abstractmethod
    def download_file(self, remote_path: str, timeout: int = 30 * 60) -> bytes:
        """Download a file from the sandbox."""
        raise NotImplementedError
