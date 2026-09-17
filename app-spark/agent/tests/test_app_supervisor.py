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

"""AppSupervisor 规则：校验、启动 spec、重启沿用、并发 409、启动失败、crash-watch。"""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import pytest

from app_spark_agent import settings
from app_spark_agent.app_supervisor import (
    APP_PORT_ENV,
    LAUNCH_EVENT_RUN_ID,
    SECRET_ENV_KEYS,
    AppLaunchConflict,
    AppLaunchFailed,
    AppLaunchInvalid,
    AppStatus,
    AppSupervisor,
    build_app_spec,
    build_child_environ,
    validate_launch_label,
    validate_launch_path,
)
from app_spark_agent.app_supervisor import process as process_mod
from app_spark_agent.app_supervisor import supervisor as supervisor_mod
from app_spark_agent.app_supervisor.app_spec import APP_IMPORT_PATH
from app_spark_agent.server.lifecycle import AppProcessRegistry
from app_spark_agent.state import AppendLog


class Child:
    def __init__(self, *, living: bool = True) -> None:
        self.living = living
        self.pid = 0

    def poll(self) -> int | None:
        return None if self.living else 0

    def terminate(self) -> None:
        self.living = False

    kill = terminate

    def wait(self, timeout: float | None = None) -> int:
        self.living = False
        return 0


class App:
    """假端口 + 假进程。auto_listen 关掉后 spawn 不再把端口标成在听。"""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        *,
        living: bool = True,
        auto_listen: bool = True,
        fail_on: int | None = None,
    ) -> None:
        self.listening = False
        self.auto_listen = auto_listen
        self.spawned: list[Child] = []
        self._living = living
        self._fail_on = fail_on
        self._calls = 0
        (tmp_path / "workspace").mkdir(exist_ok=True)
        monkeypatch.setattr(supervisor_mod, "tcp_port_is_open", lambda _port: self.listening)
        monkeypatch.setattr(process_mod, "_spawn_popen", self._spawn)
        self.supervisor = AppSupervisor(
            tmp_path / "workspace",
            AppProcessRegistry(),
            AppendLog(tmp_path / "ui_events.jsonl", payload_key="event"),
        )

    def _spawn(self, *_args: object, **_kwargs: object) -> Child:
        self._calls += 1
        if self._fail_on is not None and self._calls == self._fail_on:
            raise OSError("spawn refused")
        child = Child(living=self._living)
        self.spawned.append(child)
        if self.auto_listen and child.poll() is None:
            self.listening = True
        return child

    def drop(self) -> None:
        self.listening = False
        self.spawned[-1].living = False

    def run_ids(self) -> set[str]:
        return {record.run_id for record in self.supervisor._ui_events.read_since(0, 100)}


@pytest.fixture(autouse=True)
def fast_supervisor_timings(monkeypatch: pytest.MonkeyPatch) -> None:
    # 生产是 30s / 2s / 0.5s，单测不能真睡那么久。
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.4)
    monkeypatch.setattr(supervisor_mod, "CRASH_RETRY_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(supervisor_mod, "CRASH_WATCH_POLL_SECONDS", 0.01)


@asynccontextmanager
async def watching(supervisor: AppSupervisor) -> AsyncIterator[asyncio.Task[None]]:
    task = asyncio.create_task(supervisor.watch())
    try:
        yield task
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def wait_until(predicate: Callable[[], bool], timeout: float = 1.5) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met before timeout")


def test_path_and_label_rules() -> None:
    assert validate_launch_path("/") == "/"
    assert validate_launch_path("/preview") == "/preview"
    for path in ("preview", "//host/path", "/../secret", "https://example.com/"):
        with pytest.raises(AppLaunchInvalid):
            validate_launch_path(path)
    assert validate_launch_label(" Preview ") == "Preview"
    for label in ("", "x" * 65):
        with pytest.raises(AppLaunchInvalid):
            validate_launch_label(label)


def test_child_env_drops_every_agent_setting_not_just_the_known_secrets() -> None:
    """应用进程拿不到任何 APP_SPARK_AGENT_* —— 包括还没被认定为密钥的那些。

    逐个 pop 已知密钥的话，以后新增一个忘了登记就是静默泄漏，而应用是模型写的代码。
    """
    source = dict.fromkeys(SECRET_ENV_KEYS, "secret")
    source["APP_SPARK_AGENT_WORKSPACE"] = "/data/workspace"
    source["PATH"] = "/usr/bin"

    env = build_child_environ(8123, source)

    assert all(key not in env for key in SECRET_ENV_KEYS)
    # 不是密钥，一样不给：剥的是整个前缀。应用的 cwd 就是 workspace，不需要它。
    assert "APP_SPARK_AGENT_WORKSPACE" not in env
    # 前缀之外的环境原样继承，应用还要靠它找解释器和系统工具。
    assert env["PATH"] == "/usr/bin"
    # 端口是唯一加回来的那一项，尽管它也带这个前缀。
    assert env[APP_PORT_ENV] == "8123"


def test_spec_starts_the_import_path_the_instructions_promise(tmp_path: Path) -> None:
    """启动命令和提示词里的入口名是一对，改一边就必须改另一边，否则 launch 必失败。"""
    spec = build_app_spec(tmp_path, 8123)

    assert APP_IMPORT_PATH in spec.argv
    assert APP_IMPORT_PATH in settings.INSTRUCTIONS
    assert spec.argv[-2:] == ("--port", "8123")
    assert spec.cwd == tmp_path


async def test_relaunch_keeps_path_and_reuses_run_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path)
    first = await app.supervisor.launch(path="/demo", label="Demo")
    app.listening = False
    second = await app.supervisor.launch()
    assert (first.path, first.label) == (second.path, second.label) == ("/demo", "Demo")
    assert len(app.spawned) == 2
    assert app.spawned[0].poll() is not None
    assert app.run_ids() == {LAUNCH_EVENT_RUN_ID}


async def test_second_launch_while_waiting_is_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 1.0)
    app = App(monkeypatch, tmp_path, auto_listen=False)
    first = asyncio.create_task(app.supervisor.launch())
    await asyncio.sleep(0.05)
    with pytest.raises(AppLaunchConflict, match="already in progress"):
        await app.supervisor.launch()
    app.listening = True
    assert (await first).app_status == AppStatus.HEALTHY


@pytest.mark.parametrize(
    ("living", "match"),
    [(True, "did not listen"), (False, "exited before it listened")],
)
async def test_failed_launch_is_unhealthy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    living: bool,
    match: str,
) -> None:
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.15)
    app = App(monkeypatch, tmp_path, living=living, auto_listen=False)
    with pytest.raises(AppLaunchFailed, match=match):
        await app.supervisor.launch()
    assert app.supervisor.app_status == AppStatus.UNHEALTHY


async def test_watch_restarts_after_a_spawn_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # fail_on=2：第一次手动 launch 成功，自动重启第一次抛 OSError，第二次拉起来。
    app = App(monkeypatch, tmp_path, fail_on=2)
    await app.supervisor.launch()
    app.drop()
    async with watching(app.supervisor) as task:
        await wait_until(lambda: len(app.spawned) == 2)
        assert not task.done()
        assert app.supervisor.app_status == AppStatus.HEALTHY
        assert app.run_ids() == {LAUNCH_EVENT_RUN_ID}


async def test_watch_gives_up_after_retry_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.08)
    monkeypatch.setattr(supervisor_mod, "CRASH_RETRY_LIMIT", 2)
    app = App(monkeypatch, tmp_path)
    await app.supervisor.launch()
    app.auto_listen = False
    app.drop()
    async with watching(app.supervisor):
        await wait_until(lambda: app.supervisor._auto_restarts >= 2, timeout=2.0)
        assert app.supervisor.app_status == AppStatus.UNHEALTHY
        stopped_at = len(app.spawned)
        await asyncio.sleep(0.1)
        assert len(app.spawned) == stopped_at


async def test_watch_ignores_never_launched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path, auto_listen=False)
    async with watching(app.supervisor):
        await asyncio.sleep(0.08)
        assert app.spawned == []
        assert app.supervisor.app_status == AppStatus.NOT_STARTED
