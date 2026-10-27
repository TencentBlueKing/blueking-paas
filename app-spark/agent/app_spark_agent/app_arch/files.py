# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Shared result protocol and atomic writer for app_arch-generated files."""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from app_spark_agent.utils import write_atomic


class FileSyncStatus(StrEnum):
    """Stable statuses returned directly by architecture-backed model tools."""

    SYNCED = "synced"
    UNCHANGED = "unchanged"
    FAILED = "failed"


class AppArchErrorCode(StrEnum):
    """Machine-readable reasons for a failed architecture operation."""

    INVALID_PROJECT_NAME = "invalid_project_name"
    TEMPLATE_FAILED = "template_failed"
    WRITE_FAILED = "write_failed"


class FileSyncResult(BaseModel):
    """Result shared by every generated-file operation.

    :param status: synced wrote at least one file; unchanged found everything current; failed
        could not produce the required files.
    :param files: All files owned by the operation.
    :param changed: Files replaced before the operation completed.
    :param errcode: Stable failure reason for programmatic handling; None unless status is failed.
    :param detail: Human-readable context suitable for returning to the model.
    """

    status: FileSyncStatus
    files: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    errcode: AppArchErrorCode | None = None
    detail: str = ""


def sync_text_files(workspace: Path, rendered: Mapping[str, str]) -> FileSyncResult:
    """Create missing files and replace stale text files, each replacement atomically."""
    files = tuple(rendered)
    changed: list[str] = []
    for filename, content in rendered.items():
        path = workspace / filename
        payload = content.encode("utf-8")
        try:
            if path.is_file() and path.read_bytes() == payload:
                continue
            write_atomic(path, payload)
        except OSError as exc:
            return FileSyncResult(
                status=FileSyncStatus.FAILED,
                files=files,
                changed=tuple(changed),
                errcode=AppArchErrorCode.WRITE_FAILED,
                detail=f"Could not synchronize {filename}: {exc}",
            )
        changed.append(filename)

    status = FileSyncStatus.SYNCED if changed else FileSyncStatus.UNCHANGED
    return FileSyncResult(status=status, files=files, changed=tuple(changed))


def merge_sync_results(*results: FileSyncResult) -> FileSyncResult:
    """Combine several file operations into one tool-facing result."""
    files = _ordered_unique(name for result in results for name in result.files)
    changed = _ordered_unique(name for result in results for name in result.changed)
    failed = next((result for result in results if result.status is FileSyncStatus.FAILED), None)
    if failed is not None:
        return FileSyncResult(
            status=FileSyncStatus.FAILED,
            files=files,
            changed=changed,
            errcode=failed.errcode,
            detail=failed.detail,
        )

    status = FileSyncStatus.SYNCED if changed else FileSyncStatus.UNCHANGED
    detail = next((result.detail for result in results if result.detail), "")
    return FileSyncResult(status=status, files=files, changed=changed, detail=detail)


def _ordered_unique(names: Iterable[str]) -> tuple[str, ...]:
    """Return string items once, preserving their first-seen order."""
    return tuple(dict.fromkeys(names))
