"""The model's init_project tool: a thin adapter over AppArchitecture.init_project.

What the project files contain is covered in tests/app_arch/test_python.py, and how project
creation and platform configuration combine in tests/app_arch/test_architecture.py.
"""

from pathlib import Path

from app_spark_agent.app_arch.app_desc import render_app_desc
from app_spark_agent.app_arch.architecture import SYNC_FILENAMES
from app_spark_agent.app_arch.files import FileSyncResult, FileSyncStatus
from app_spark_agent.app_arch.python import PYTHON_PROJECT_FILES, PYTHON_VERSION, PYTHON_VERSION_FILENAME
from app_spark_agent.tools.init_project import build_init_project_tool

INITIALIZED_FILES = (*PYTHON_PROJECT_FILES, *SYNC_FILENAMES)


def test_tool_creates_the_python_project_and_platform_configuration(tmp_path: Path) -> None:
    init_project = build_init_project_tool(tmp_path)

    result = init_project("Todo Board")

    assert result == FileSyncResult(
        status=FileSyncStatus.SYNCED,
        files=INITIALIZED_FILES,
        changed=INITIALIZED_FILES,
        detail="Created Python project todo-board.",
    )
    assert {path.name for path in tmp_path.iterdir()} == set(INITIALIZED_FILES)
    assert (tmp_path / "app_desc.yaml").read_text() == render_app_desc()
    assert (tmp_path / PYTHON_VERSION_FILENAME).read_text() == f"{PYTHON_VERSION}\n"
