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

"""Launching the workspace application through the model's own launch_app tool."""

import socket
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient

from app_spark_agent import settings
from app_spark_agent.app_supervisor import LAUNCH_EVENT_RUN_ID
from app_spark_agent.app_supervisor import supervisor as supervisor_mod
from app_spark_agent.tools import MAX_LAUNCHES_PER_RUN, LaunchToolResult
from tests.api.support import ApiFactory, drain_channel, run_turn
from tests.support.fake_models import named_tool_model

MINIMAL_APP = """
import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict[str, str]:
    return {"port": os.environ["APP_SPARK_AGENT_APP_PORT"]}
"""


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def workspace_of(client: TestClient) -> Path:
    return Path(client.app.state.conversation_runtime.app_supervisor.workspace)


def write_minimal_app(workspace: Path) -> None:
    (workspace / "main.py").write_text(MINIMAL_APP)


def launched_records(client: TestClient) -> list[dict[str, Any]]:
    return [record for record in drain_channel(client, "/ui-events") if record["event"].get("name") == "app.launched"]


def launched_events(client: TestClient) -> list[dict[str, Any]]:
    return [record["event"] for record in launched_records(client)]


class ModelLauncher:
    """The model's launch tool, wired the way a real agent gets it, plus what it returned.

    An injected agent is built before the Runtime exists, so the tool reaches the Runtime's own
    LaunchTool through client at call time -- during the run, by when everything is wired.
    """

    def __init__(self) -> None:
        self.client: TestClient | None = None
        self.results: list[LaunchToolResult] = []

        async def launch_app() -> LaunchToolResult:
            """Start or restart this session's application and report whether it is listening."""
            assert self.client is not None

            # 调生产的 as_tool()，不复刻那层包装；这里只负责把结果记下来。
            launch_tool = self.client.app.state.conversation_runtime.launch_tool
            result = await launch_tool.as_tool()()
            self.results.append(result)
            return result

        self.tool: Callable[[], Any] = launch_app

    def serving(self, api: TestClient) -> TestClient:
        """Point the tool at a started Runtime and hand that client back."""
        self.client = api
        return api


@pytest.fixture(autouse=True)
def project_environment_without_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the uv sync before each launch, keeping the real spawn.

    A real sync needs the package index or a warm uv cache, neither of which a unit test can
    count on. The test interpreter already has fastapi and uvicorn, so the project's interpreter
    hands over to it. The real uv path is covered by tests/test_project_env.py and the images.
    """

    async def use_test_interpreter(workspace: Path, _log_path: Path) -> None:
        python = workspace / ".venv" / "bin" / "python"
        if python.exists():
            return
        python.parent.mkdir(parents=True)
        # exec rather than a symlink: Python finds its venv next to the path it was started as,
        # and a symlink with no pyvenv.cfg beside it resolves to the base interpreter instead.
        python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        python.chmod(0o755)

    monkeypatch.setattr(supervisor_mod, "sync_project_environment", use_test_interpreter)


@pytest.fixture
def launch_port(monkeypatch: pytest.MonkeyPatch) -> int:
    port = unused_port()
    monkeypatch.setattr(settings, "APP_PORT", port)
    return port


def test_the_model_launches_the_app_itself(make_api: ApiFactory, launch_port: int) -> None:
    """The point of the tool: the turn that writes the code also gets it serving."""
    launcher = ModelLauncher()
    api = launcher.serving(make_api(model=named_tool_model("launch_app"), tools=[launcher.tool]))
    write_minimal_app(workspace_of(api))

    run_turn(api, conversation_id=str(uuid4()))

    assert [result.status for result in launcher.results] == ["ok"]
    assert launcher.results[0].port == launch_port
    assert httpx2.get(f"http://127.0.0.1:{launch_port}/").json()["port"] == str(launch_port)
    assert api.get("/health").json()["dev_server_status"] == "ready"

    # 回写通道就是控制面已经在 drain 的那条，不需要反向回调。
    records = launched_records(api)
    assert len(records) == 1
    assert records[0]["run_id"] == LAUNCH_EVENT_RUN_ID
    assert records[0]["event"]["value"] == {
        "port": launch_port,
        "path": "/",
        "label": "Preview",
        "dev_server_status": "ready",
    }


def test_the_model_can_launch_twice_in_one_turn(make_api: ApiFactory, launch_port: int) -> None:
    """重启是为了加载新代码，但这里验的是第二次 launch 本身成功、且应用仍在服务。"""
    launcher = ModelLauncher()
    api = launcher.serving(make_api(model=named_tool_model("launch_app", times=2), tools=[launcher.tool]))
    write_minimal_app(workspace_of(api))

    run_turn(api, conversation_id=str(uuid4()))

    assert [result.status for result in launcher.results] == ["ok", "ok"]
    assert httpx2.get(f"http://127.0.0.1:{launch_port}/").json()["port"] == str(launch_port)


def test_a_foreign_port_is_reported_as_failed(make_api: ApiFactory, launch_port: int) -> None:
    launcher = ModelLauncher()
    api = launcher.serving(make_api(model=named_tool_model("launch_app"), tools=[launcher.tool]))
    write_minimal_app(workspace_of(api))
    occupant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupant.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    occupant.bind(("127.0.0.1", launch_port))
    occupant.listen(1)
    try:
        run_turn(api, conversation_id=str(uuid4()))

        assert [result.status for result in launcher.results] == ["failed"]
        assert "owned by a process" in launcher.results[0].detail
        assert api.get("/health").json()["dev_server_status"] == "not_started"
        assert launched_events(api) == []
    finally:
        occupant.close()


def test_missing_app_is_failed(make_api: ApiFactory, launch_port: int) -> None:
    launcher = ModelLauncher()
    api = launcher.serving(make_api(model=named_tool_model("launch_app"), tools=[launcher.tool]))

    run_turn(api, conversation_id=str(uuid4()))

    assert [result.status for result in launcher.results] == ["failed"]
    assert api.get("/health").json()["dev_server_status"] == "stopped"
    assert launched_events(api) == []


def test_the_model_cannot_retry_launching_all_turn(make_api: ApiFactory, launch_port: int) -> None:
    """Failure makes a model rewrite and relaunch; without a cap that burns the whole turn."""
    launcher = ModelLauncher()
    attempts = MAX_LAUNCHES_PER_RUN + 1
    # workspace 里没有 main.py：每次都起不来，模型会一直想再试。
    api = launcher.serving(
        make_api(model=named_tool_model("launch_app", times=attempts), tools=[launcher.tool]),
    )

    run_turn(api, conversation_id=str(uuid4()))

    # 额度用尽后第三次直接被拒，run 本身照常结束。下一轮重新给额度见 tests/tools/test_launch_app.py。
    assert [result.status for result in launcher.results] == ["failed"] * MAX_LAUNCHES_PER_RUN + ["refused"]
    assert api.get("/health").json()["dev_server_status"] == "stopped"
    assert launched_events(api) == []
