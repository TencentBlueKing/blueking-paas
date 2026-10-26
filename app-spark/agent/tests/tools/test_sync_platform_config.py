"""The model-facing adapter for architecture-file synchronization."""

from pathlib import Path

from app_spark_agent.app_arch.architecture import SYNC_FILENAMES
from app_spark_agent.app_arch.files import FileSyncResult, FileSyncStatus
from app_spark_agent.tools.sync_platform_config import build_sync_platform_config_tool


def test_model_tool_reports_what_it_repaired(tmp_path: Path) -> None:
    tool = build_sync_platform_config_tool(tmp_path, port=5000)

    result = tool()

    assert type(result) is FileSyncResult
    assert result == FileSyncResult(
        status=FileSyncStatus.SYNCED,
        files=SYNC_FILENAMES,
        changed=SYNC_FILENAMES,
    )
    assert tool() == FileSyncResult(status=FileSyncStatus.UNCHANGED, files=SYNC_FILENAMES)
