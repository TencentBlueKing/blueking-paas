"""Developer Center manifest rendering and the AppArchitecture entry point."""

import shlex
from pathlib import Path

import pytest

from app_spark_agent import settings
from app_spark_agent.app_arch.app_desc import APP_DESC_FILENAME, DEPLOY_PORT, render_app_desc
from app_spark_agent.app_arch.architecture import SYNC_FILENAMES, AppArchitecture
from app_spark_agent.app_arch.files import AppArchErrorCode, FileSyncResult, FileSyncStatus
from app_spark_agent.app_arch.python import (
    EXISTS_DETAIL,
    PYTHON_PROJECT_FILES,
    PYTHON_VERSION,
    PYTHON_VERSION_FILENAME,
    build_proc_command,
)
from app_spark_agent.app_supervisor.app_spec import build_app_spec


def test_app_desc_contains_the_canonical_command_and_service_port(tmp_path: Path) -> None:
    spec = build_app_spec(tmp_path, DEPLOY_PORT)

    assert build_proc_command(DEPLOY_PORT) == shlex.join(("python", *spec.argv[1:]))
    assert (
        render_app_desc()
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

    created = architecture.sync()

    assert created.status is FileSyncStatus.SYNCED
    assert created.files == SYNC_FILENAMES
    assert created.changed == SYNC_FILENAMES
    assert (tmp_path / APP_DESC_FILENAME).read_text() == render_app_desc()
    assert (tmp_path / PYTHON_VERSION_FILENAME).read_text() == f"{PYTHON_VERSION}\n"

    (tmp_path / APP_DESC_FILENAME).write_text("stale\n")
    (tmp_path / PYTHON_VERSION_FILENAME).unlink()
    repaired = architecture.sync()

    assert repaired.status is FileSyncStatus.SYNCED
    assert repaired.changed == SYNC_FILENAMES
    assert (tmp_path / APP_DESC_FILENAME).read_text() == render_app_desc()
    before = {name: (tmp_path / name).stat().st_mtime_ns for name in SYNC_FILENAMES}

    unchanged = architecture.sync()

    assert unchanged.status is FileSyncStatus.UNCHANGED
    assert unchanged.changed == ()
    assert {name: (tmp_path / name).stat().st_mtime_ns for name in SYNC_FILENAMES} == before


def test_init_on_an_existing_project_keeps_it_but_repairs_platform_configuration(tmp_path: Path) -> None:
    """A retry after a half-finished init_project must finish the platform files, not stop early."""
    architecture = AppArchitecture(tmp_path)
    (tmp_path / "pyproject.toml").write_text("# the user's own\n")

    assert architecture.init_project("todo-board") == FileSyncResult(
        status=FileSyncStatus.SYNCED,
        files=(*PYTHON_PROJECT_FILES, *SYNC_FILENAMES),
        changed=SYNC_FILENAMES,
        detail=EXISTS_DETAIL,
    )
    assert (tmp_path / "pyproject.toml").read_text() == "# the user's own\n"
    assert not (tmp_path / "uv.lock").exists()
    assert (tmp_path / APP_DESC_FILENAME).read_text() == render_app_desc()

    assert architecture.init_project("todo-board") == FileSyncResult(
        status=FileSyncStatus.UNCHANGED,
        files=(*PYTHON_PROJECT_FILES, *SYNC_FILENAMES),
        detail=EXISTS_DETAIL,
    )


def test_init_that_cannot_create_the_project_writes_no_platform_configuration(tmp_path: Path) -> None:
    result = AppArchitecture(tmp_path).init_project("待办看板")

    assert result.status is FileSyncStatus.FAILED
    assert result.errcode is AppArchErrorCode.INVALID_PROJECT_NAME
    assert list(tmp_path.iterdir()) == []


def test_app_desc_does_not_follow_the_preview_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """app_desc.yaml is saved with the code; the sandbox a launch ran in must not leave a diff."""
    monkeypatch.setattr(settings, "APP_PORT", 8123)

    AppArchitecture(tmp_path).sync()

    assert (tmp_path / APP_DESC_FILENAME).read_text() == render_app_desc()
    assert "8123" not in render_app_desc()
