"""The shared result and writer used by app_arch modules."""

from pathlib import Path

import pytest

from app_spark_agent.app_arch import files as files_mod
from app_spark_agent.app_arch.files import (
    AppArchErrorCode,
    FileSyncResult,
    FileSyncStatus,
    sync_text_files,
)


def test_write_failure_is_returned_instead_of_raised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(_path: Path, _data: bytes) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(files_mod, "write_atomic", fail_write)

    result = sync_text_files(tmp_path, {"app_desc.yaml": "content\n"})

    assert result == FileSyncResult(
        status=FileSyncStatus.FAILED,
        files=("app_desc.yaml",),
        errcode=AppArchErrorCode.WRITE_FAILED,
        detail="Could not synchronize app_desc.yaml: disk full",
    )
