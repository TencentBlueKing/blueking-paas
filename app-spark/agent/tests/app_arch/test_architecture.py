"""Developer Center manifest rendering and the AppArchitecture entry point."""

import shlex
from pathlib import Path

from app_spark_agent.app_arch.app_desc import APP_DESC_FILENAME, render_app_desc, sync_app_desc
from app_spark_agent.app_arch.architecture import SYNC_FILENAMES, AppArchitecture
from app_spark_agent.app_arch.files import FileSyncResult, FileSyncStatus
from app_spark_agent.app_arch.python import (
    PYTHON_VERSION,
    PYTHON_VERSION_FILENAME,
    build_proc_command,
    sync_python_version,
)
from app_spark_agent.app_supervisor.app_spec import build_app_spec


def test_app_desc_contains_the_canonical_command_and_service_port(tmp_path: Path) -> None:
    spec = build_app_spec(tmp_path, 5000)

    assert build_proc_command(5000) == shlex.join(("python", *spec.argv[1:]))
    assert (
        render_app_desc(5000)
        == """specVersion: 3
module:
  language: Python
  spec:
    processes:
      - name: web
        procCommand: python -m uvicorn main:app --host 0.0.0.0 --port 5000
        services:
          - name: web
            exposedType:
              name: bk/http
            targetPort: 5000
            port: 80
"""
    )


def test_sync_creates_repairs_and_then_leaves_architecture_files_alone(tmp_path: Path) -> None:
    architecture = AppArchitecture(tmp_path)

    created = architecture.sync(5000)

    assert created.status is FileSyncStatus.SYNCED
    assert created.files == SYNC_FILENAMES
    assert created.changed == SYNC_FILENAMES
    assert (tmp_path / APP_DESC_FILENAME).read_text() == render_app_desc(5000)
    assert (tmp_path / PYTHON_VERSION_FILENAME).read_text() == f"{PYTHON_VERSION}\n"

    (tmp_path / APP_DESC_FILENAME).write_text("stale\n")
    (tmp_path / PYTHON_VERSION_FILENAME).unlink()
    repaired = architecture.sync(8123)

    assert repaired.status is FileSyncStatus.SYNCED
    assert repaired.changed == SYNC_FILENAMES
    assert "targetPort: 8123" in (tmp_path / APP_DESC_FILENAME).read_text()
    before = {name: (tmp_path / name).stat().st_mtime_ns for name in SYNC_FILENAMES}

    unchanged = architecture.sync(8123)

    assert unchanged.status is FileSyncStatus.UNCHANGED
    assert unchanged.changed == ()
    assert {name: (tmp_path / name).stat().st_mtime_ns for name in SYNC_FILENAMES} == before


def test_owner_modules_use_the_shared_file_result(tmp_path: Path) -> None:
    app_desc_result = sync_app_desc(tmp_path, 5000)
    python_result = sync_python_version(tmp_path)

    assert type(app_desc_result) is FileSyncResult
    assert type(python_result) is FileSyncResult
    assert app_desc_result.status is python_result.status is FileSyncStatus.SYNCED
