"""The model's init_project tool: the name it accepts, the files it writes, what it reports back."""

from pathlib import Path

from app_spark_agent import settings
from app_spark_agent.app_arch.app_desc import render_app_desc
from app_spark_agent.app_arch.architecture import SYNC_FILENAMES
from app_spark_agent.app_arch.files import AppArchErrorCode, FileSyncResult, FileSyncStatus
from app_spark_agent.app_arch.python import (
    EXISTS_DETAIL,
    PYTHON_PROJECT_FILES,
    PYTHON_VERSION,
    PYTHON_VERSION_FILENAME,
    REPLACED_LOCK_DETAIL,
)
from app_spark_agent.tools.init_project import build_init_project_tool

INITIALIZED_FILES = (*PYTHON_PROJECT_FILES, *SYNC_FILENAMES)


def test_tool_creates_the_python_project_and_platform_configuration(tmp_path: Path) -> None:
    init_project = build_init_project_tool(tmp_path)

    result = init_project("Todo Board")

    assert type(result) is FileSyncResult
    assert result == FileSyncResult(
        status=FileSyncStatus.SYNCED,
        files=INITIALIZED_FILES,
        changed=INITIALIZED_FILES,
        detail="Created Python project todo-board.",
    )
    assert {path.name for path in tmp_path.iterdir()} == set(INITIALIZED_FILES)
    assert (tmp_path / "app_desc.yaml").read_text() == render_app_desc(settings.APP_PORT)
    assert (tmp_path / PYTHON_VERSION_FILENAME).read_text() == f"{PYTHON_VERSION}\n"


def test_tool_leaves_an_existing_project_alone(tmp_path: Path) -> None:
    init_project = build_init_project_tool(tmp_path)
    (tmp_path / "pyproject.toml").write_text("# the user's own\n")

    assert init_project("todo-board") == FileSyncResult(
        status=FileSyncStatus.UNCHANGED,
        files=PYTHON_PROJECT_FILES,
        detail=EXISTS_DETAIL,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml"]


def test_tool_reports_replacing_an_orphaned_lock(tmp_path: Path) -> None:
    init_project = build_init_project_tool(tmp_path)
    (tmp_path / "uv.lock").write_text("# left behind\n")

    assert init_project("todo-board") == FileSyncResult(
        status=FileSyncStatus.SYNCED,
        files=INITIALIZED_FILES,
        changed=INITIALIZED_FILES,
        detail=f"Created Python project todo-board. {REPLACED_LOCK_DETAIL}",
    )
    assert {path.name for path in tmp_path.iterdir()} == set(INITIALIZED_FILES)


def test_invalid_name_is_handed_back_instead_of_raised(tmp_path: Path) -> None:
    """Raising out of a tool ends the turn; the model can simply pick another name."""
    result = build_init_project_tool(tmp_path)("待办看板")

    assert result.status is FileSyncStatus.FAILED
    assert result.errcode == AppArchErrorCode.INVALID_PROJECT_NAME
    assert "for example `todo-board`" in result.detail
    assert list(tmp_path.iterdir()) == []
