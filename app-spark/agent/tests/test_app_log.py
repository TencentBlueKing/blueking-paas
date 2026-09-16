"""用户应用日志：只读约定文件、截尾 8KB、不碰 workspace / state。

这里的应用是用户用自然语言编出来、跑在沙箱里的那个服务，不是 Agent 进程。
"""

from pathlib import Path

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai_harness import FileSystem
from pytest import MonkeyPatch

from app_spark_agent import settings
from app_spark_agent.agent import create_agent
from app_spark_agent.app_log import NO_LOG_MESSAGE, READ_ERROR_PREFIX, AppLogReader
from app_spark_agent.masking import SECRET_PLACEHOLDER
from tests.test_agent import function_tools


def test_missing_or_empty_file_is_reported_as_no_log(tmp_path: Path) -> None:
    missing = AppLogReader(tmp_path / "missing.log")
    empty_path = tmp_path / "empty.log"
    empty_path.write_bytes(b"")

    assert missing.read().content == NO_LOG_MESSAGE
    assert missing.read().status == "empty"
    assert AppLogReader(empty_path).read().status == "empty"
    assert AppLogReader(empty_path).read().content == NO_LOG_MESSAGE


def test_a_short_file_is_returned_in_full(tmp_path: Path) -> None:
    path = tmp_path / "app.log"
    path.write_bytes(b"hello-log")

    result = AppLogReader(path).read()

    assert result.status == "ok"
    assert result.content == "hello-log"
    assert result.truncated is False
    assert result.byte_length == 9


def test_an_oversized_file_keeps_the_tail(tmp_path: Path) -> None:
    path = tmp_path / "app.log"
    body = b"H" * 100 + b"T" * 8192
    path.write_bytes(body)

    result = AppLogReader(path).read()

    assert result.status == "ok"
    assert result.truncated is True
    assert result.byte_length == settings.APP_LOG_MAX_BYTES
    assert result.content.encode() == body[-8192:]
    assert result.content.startswith("T")
    assert "H" not in result.content


def test_a_directory_is_reported_as_read_failure(tmp_path: Path) -> None:
    result = AppLogReader(tmp_path).read()

    assert result.status == "error"
    assert result.content.startswith(READ_ERROR_PREFIX)


def test_a_symlink_into_state_is_reported_as_read_failure(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    log_path = tmp_path / "app.log"
    workspace.mkdir()
    state.mkdir()
    marker = "STATE-SECRET-7c1a"
    (state / "context.json").write_text(marker)
    log_path.write_text("app-ok")
    reader = AppLogReader(log_path, workspace=workspace, state_dir=state)
    log_path.unlink()
    log_path.symlink_to(state / "context.json")

    result = reader.read()

    assert result.status == "error"
    assert result.content.startswith(READ_ERROR_PREFIX)
    assert marker not in result.content


def test_log_content_masks_configured_credentials(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    path = tmp_path / "app.log"
    token = "runtime-token-should-not-reach-the-model"
    path.write_text(f"crash token={token}")
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", token)
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "CONTROL_PLANE_TOKEN", None)

    result = AppLogReader(path).read()

    assert result.status == "ok"
    assert token not in result.content
    assert SECRET_PLACEHOLDER in result.content


def test_the_configured_path_cannot_sit_inside_workspace_or_state(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    workspace.mkdir()
    state.mkdir()

    with pytest.raises(ValueError, match="workspace"):
        AppLogReader(workspace / "app.log", workspace=workspace, state_dir=state)
    with pytest.raises(ValueError, match="state"):
        AppLogReader(state / "context.json", workspace=workspace, state_dir=state)


def test_the_log_tool_cannot_see_state_and_file_tools_cannot_see_the_log(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    log_path = tmp_path / "app.log"
    workspace.mkdir()
    state.mkdir()
    marker = "STATE-MARKER-9f3c"
    (state / "context.json").write_text(f'{{"secret": "{marker}"}}')
    log_path.write_text("app-ok")
    monkeypatch.setattr(settings, "APP_LOG_PATH", log_path)
    monkeypatch.setattr(settings, "MODEL_API_KEY", "not-used-by-this-test")
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "")

    agent = create_agent(workspace, state_dir=state)
    result = function_tools(agent)["read_app_log"].function()

    assert result.content == "app-ok"
    assert marker not in result.content

    filesystem = next(item for item in agent.root_capability.capabilities if isinstance(item, FileSystem))
    toolset = filesystem.get_toolset()
    inner = getattr(toolset, "wrapped", toolset)
    while hasattr(inner, "wrapped"):
        inner = inner.wrapped
    for outside in (f"../{log_path.name}", str(log_path), f"../{state.name}/context.json"):
        with pytest.raises((PermissionError, ModelRetry), match="outside"):
            inner._resolve_path(outside)
