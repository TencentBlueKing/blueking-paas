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

"""AppSupervisor 规则：校验、密钥剥离、重启沿用、并发 409、启动失败。"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app_spark_agent import settings
from app_spark_agent.app_supervisor import (
    APP_PORT_ENV,
    SECRET_ENV_KEYS,
    AppLaunchConflict,
    AppLaunchFailed,
    AppLaunchInvalid,
    AppStatus,
    AppSupervisor,
    validate_launch_label,
    validate_launch_path,
)
from app_spark_agent.server.lifecycle import AppProcessRegistry
from app_spark_agent.state import AppendLog


class FakeProcess:
    def __init__(self, *, living: bool = True) -> None:
        self._living = living
        self.pid = 0

    def poll(self) -> int | None:
        return None if self._living else 0

    def terminate(self) -> None:
        self._living = False

    def kill(self) -> None:
        self._living = False

    def wait(self, timeout: float | None = None) -> int:
        self._living = False
        return 0


def make_supervisor(
    tmp_path: Path,
    *,
    connect: Any = None,
    spawn: Any = None,
    listen_timeout: float = 0.4,
) -> AppSupervisor:
    log = AppendLog(tmp_path / "ui_events.jsonl", payload_key="event")
    return AppSupervisor(
        tmp_path / "workspace",
        AppProcessRegistry(),
        log,
        connect=connect,
        spawn=spawn,
        listen_timeout=listen_timeout,
    )


def test_path_and_label_rules() -> None:
    assert validate_launch_path("/") == "/"
    assert validate_launch_path("/preview") == "/preview"
    with pytest.raises(AppLaunchInvalid):
        validate_launch_path("preview")
    with pytest.raises(AppLaunchInvalid):
        validate_launch_path("//host/path")
    with pytest.raises(AppLaunchInvalid):
        validate_launch_path("/../secret")
    with pytest.raises(AppLaunchInvalid):
        validate_launch_path("https://example.com/")
    assert validate_launch_label(" Preview ") == "Preview"
    with pytest.raises(AppLaunchInvalid):
        validate_launch_label("")
    with pytest.raises(AppLaunchInvalid):
        validate_launch_label("x" * 65)


def test_build_child_environ_injects_port_and_drops_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "APP_PORT", 8123)
    supervisor = make_supervisor(tmp_path, connect=lambda: False)
    source = {
        "PATH": "/bin",
        "APP_SPARK_AGENT_WORKSPACE": "/data/workspace",
        "APP_SPARK_AGENT_RUNTIME_TOKEN": "runtime-secret",
        "APP_SPARK_AGENT_MODEL_API_KEY": "model-secret",
        "APP_SPARK_AGENT_AIDEV_ACCESS_TOKEN": "aidev-secret",
        "APP_SPARK_AGENT_CONTROL_PLANE_TOKEN": "plane-secret",
    }

    env = supervisor.build_child_environ(source)

    assert env[APP_PORT_ENV] == "8123"
    assert env["APP_SPARK_AGENT_WORKSPACE"] == "/data/workspace"
    for key in SECRET_ENV_KEYS:
        assert key not in env


async def test_relaunch_restarts_and_keeps_last_path(tmp_path: Path) -> None:
    listening = False
    spawned: list[FakeProcess] = []

    def spawn(*_args: object, **_kwargs: object) -> FakeProcess:
        nonlocal listening
        process = FakeProcess()
        spawned.append(process)
        listening = True
        return process

    supervisor = make_supervisor(tmp_path, connect=lambda: listening, spawn=spawn)
    (tmp_path / "workspace").mkdir()

    first = await supervisor.launch(path="/demo", label="Demo")

    # 第二次不带 path/label：沿用上次，并先停掉旧进程。
    listening = False
    second = await supervisor.launch()

    assert first.path == "/demo"
    assert first.label == "Demo"
    assert second.path == "/demo"
    assert second.label == "Demo"
    assert len(spawned) == 2
    assert spawned[0].poll() is not None


async def test_second_launch_while_waiting_is_conflict(tmp_path: Path) -> None:
    listening = False
    supervisor = make_supervisor(
        tmp_path,
        connect=lambda: listening,
        spawn=lambda *_args, **_kwargs: FakeProcess(),
        listen_timeout=1.0,
    )
    (tmp_path / "workspace").mkdir()

    # 第一次卡在等实听，锁还没放。第二次必须 409，不能排队。
    first = asyncio.create_task(supervisor.launch())
    await asyncio.sleep(0.05)
    with pytest.raises(AppLaunchConflict, match="already in progress"):
        await supervisor.launch()

    listening = True
    result = await first
    assert result.app_status == AppStatus.HEALTHY


async def test_timeout_without_listen_is_unhealthy(tmp_path: Path) -> None:
    # 进程还活着，但端口一直没听上。
    supervisor = make_supervisor(
        tmp_path,
        connect=lambda: False,
        spawn=lambda *_args, **_kwargs: FakeProcess(),
        listen_timeout=0.15,
    )
    (tmp_path / "workspace").mkdir()

    with pytest.raises(AppLaunchFailed, match="did not listen"):
        await supervisor.launch()
    assert supervisor.app_status == AppStatus.UNHEALTHY


async def test_process_exit_before_listen_is_unhealthy(tmp_path: Path) -> None:
    # 进程先退出，不应空等到 listen_timeout。
    supervisor = make_supervisor(
        tmp_path,
        connect=lambda: False,
        spawn=lambda *_args, **_kwargs: FakeProcess(living=False),
        listen_timeout=0.4,
    )
    (tmp_path / "workspace").mkdir()

    with pytest.raises(AppLaunchFailed, match="exited before it listened"):
        await supervisor.launch()
    assert supervisor.app_status == AppStatus.UNHEALTHY
