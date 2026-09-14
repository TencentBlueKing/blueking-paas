"""POST /runs 必须能按结构消费 read_app_log 的返回。"""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app_spark_agent.app_log import NO_LOG_MESSAGE, AppLogReader, AppLogReadResult
from tests.api.support import ApiFactory, get_transcript_messages, run_turn
from tests.support.fake_models import log_calling_model


def _read_app_log_tool(path: Path):
    reader = AppLogReader(path)

    def read_app_log() -> AppLogReadResult:
        """Read this session's application log. The path is not a parameter."""
        return reader.read()

    return read_app_log


def _tool_return_payloads(api: TestClient) -> list[object]:
    payloads: list[object] = []
    for message in get_transcript_messages(api):
        for part in message["parts"]:
            if part.get("part_kind") == "tool-return":
                payloads.append(part.get("content"))
    return payloads


def _as_result(payload: object) -> dict[str, object]:
    parsed: object = payload
    if isinstance(parsed, str):
        parsed = json.loads(parsed)
    assert isinstance(parsed, dict)
    return parsed


def test_a_run_consumes_a_structured_app_log_result(make_api: ApiFactory, tmp_path: Path) -> None:
    log_path = tmp_path / "outside" / "app.log"
    log_path.parent.mkdir()
    log_path.write_text("preview-5xx")
    api = make_api(model=log_calling_model(), tools=[_read_app_log_tool(log_path)])

    outcome = run_turn(api, conversation_id=str(uuid4()), prompt="read the app log")
    returned = _tool_return_payloads(api)

    assert "TOOL_CALL_RESULT" in outcome.event_types
    assert outcome.reply == "log-consumed"
    assert returned
    parsed = _as_result(returned[0])
    assert parsed["status"] == "ok"
    assert parsed["content"] == "preview-5xx"
    assert parsed["truncated"] is False


def test_a_run_reports_no_log_without_failing(make_api: ApiFactory, tmp_path: Path) -> None:
    log_path = tmp_path / "outside" / "app.log"
    log_path.parent.mkdir()
    api = make_api(model=log_calling_model(), tools=[_read_app_log_tool(log_path)])

    outcome = run_turn(api, conversation_id=str(uuid4()))
    returned = _tool_return_payloads(api)

    assert outcome.reply == "log-consumed"
    parsed = _as_result(returned[0])
    assert parsed["status"] == "empty"
    assert parsed["content"] == NO_LOG_MESSAGE
