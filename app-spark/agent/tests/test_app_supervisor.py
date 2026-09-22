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
    AppLaunchConflict,
    AppLaunchFailed,
    AppStatus,
    AppSupervisor,
    build_app_spec,
    build_child_environ,
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

        async def answers(_port: int) -> bool:
            return self.listening

        # 两个探针都假掉：一个判就绪（应答得了 HTTP），一个判端口有没有被占。真实情况里两者可以
        # 不一致——「占着端口但不说 HTTP」正是留下 TCP 探针的理由，那条由 test_app_probe.py 守。
        monkeypatch.setattr(supervisor_mod, "http_get_answers", answers)
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


def test_child_env_drops_every_agent_setting_not_just_the_known_secrets() -> None:
    """应用进程拿不到任何 APP_SPARK_AGENT_*，包括还没被认定为密钥的那些。"""

    # 写全名而不是拿生产常量拼：被剥掉的是前缀，名字由这里独立列出来才算校验。
    secrets = (
        "APP_SPARK_AGENT_RUNTIME_TOKEN",
        "APP_SPARK_AGENT_MODEL_API_KEY",
        "APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN",
        "APP_SPARK_AGENT_CONTROL_PLANE_TOKEN",
    )
    source = dict.fromkeys(secrets, "secret")
    source["APP_SPARK_AGENT_WORKSPACE"] = "/data/workspace"
    source["PATH"] = "/usr/bin"

    env = build_child_environ(8123, source)

    assert all(key not in env for key in secrets)
    # 不是密钥，一样不给。应用的 cwd 就是 workspace。
    assert "APP_SPARK_AGENT_WORKSPACE" not in env
    assert env["PATH"] == "/usr/bin"
    # 唯一加回来的一项，尽管它也带前缀。
    assert env[APP_PORT_ENV] == "8123"


def test_spec_starts_the_import_path_the_instructions_promise(tmp_path: Path) -> None:
    """启动命令和提示词里的入口名是一对，改一边就必须改另一边，否则 launch 必失败。"""
    spec = build_app_spec(tmp_path, 8123)

    assert APP_IMPORT_PATH in spec.argv
    assert APP_IMPORT_PATH in settings.INSTRUCTIONS
    assert spec.argv[-2:] == ("--port", "8123")
    assert spec.cwd == tmp_path


async def test_relaunch_replaces_the_process_and_reuses_the_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = App(monkeypatch, tmp_path)
    first = await app.supervisor.launch()
    app.listening = False

    second = await app.supervisor.launch()

    assert (first.path, first.label) == (second.path, second.label) == ("/", "Preview")
    assert len(app.spawned) == 2
    # 旧进程必须真的被换掉，否则「再次 launch 加载新代码」这条就不成立。
    assert app.spawned[0].poll() is not None
    # 固定哨兵，不是每次 launch 灌一个新 uuid 进 AppendLog._run_ids。
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
    assert await app.supervisor.app_status() == AppStatus.UNHEALTHY


async def test_watch_restarts_after_a_spawn_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # fail_on=2：第一次手动 launch 成功，自动重启第一次抛 OSError，第二次拉起来。
    app = App(monkeypatch, tmp_path, fail_on=2)
    await app.supervisor.launch()
    app.drop()
    async with watching(app.supervisor) as task:
        await wait_until(lambda: len(app.spawned) == 2)
        assert not task.done()
        assert await app.supervisor.app_status() == AppStatus.HEALTHY
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
        assert await app.supervisor.app_status() == AppStatus.UNHEALTHY
        stopped_at = len(app.spawned)
        await asyncio.sleep(0.1)
        assert len(app.spawned) == stopped_at


async def test_watch_ignores_never_launched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path, auto_listen=False)
    async with watching(app.supervisor):
        await asyncio.sleep(0.08)
        assert app.spawned == []
        assert await app.supervisor.app_status() == AppStatus.NOT_STARTED
