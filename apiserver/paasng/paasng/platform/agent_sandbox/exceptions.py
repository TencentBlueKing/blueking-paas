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


class SandboxError(Exception):
    """The base exception for agent sandbox errors."""


class SandboxCreateTimeout(SandboxError):
    """Raised when creating a sandbox times out."""


class SandboxAlreadyExists(SandboxError):
    """Raised when a sandbox already exists."""


class SandboxCreateError(SandboxError):
    """Raised when creating a sandbox fails."""

    def __init__(self, message: str, logs: str | None = None):
        super().__init__(message)
        self.logs = logs


class SandboxFileError(SandboxError):
    """Raised when file operations in the sandbox fail."""


class SandboxExecError(SandboxError):
    """Raised when executing a command in the sandbox fails."""


class SandboxExecTimeout(SandboxError):
    """Raised when executing a command in the sandbox times out."""


class SandboxServiceNotReady(SandboxError):
    """Raised when the sandbox daemon service is not ready (e.g., 502 Bad Gateway)."""


class SandboxDaemonAPIError(SandboxError):
    """Raised when the sandbox daemon API returns an error.

    :param status_code: HTTP status code returned by the daemon; ``None`` for transport-level
        failures (e.g. connection refused) where no response was received.
    :param detail: Human-readable detail extracted from the daemon response body, if any.
    """

    def __init__(self, message: str, *, status_code: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class SandboxImageValidateError(SandboxError):
    """Raised when snapshot image validation fails (e.g., not found, external registry, unsupported format)."""


class SandboxFileNotFound(SandboxError):
    """Raised when the target file does not exist in the volume."""


class SandboxFileTooLarge(SandboxError):
    """Raised when the target file exceeds the archive size limit."""


class SandboxFileNotPreviewable(SandboxError):
    """Raised when the target file is not previewable (e.g., a non-text type)."""


class SandboxArchiveFailed(SandboxError):
    """Raised when archiving a volume file to bkrepo fails."""


class ImageBuildSourceError(SandboxError):
    """Raised when preparing image build source fails (e.g. missing Dockerfile)."""
