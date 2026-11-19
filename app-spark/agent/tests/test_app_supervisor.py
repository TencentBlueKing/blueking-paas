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

"""AppSupervisor 规则：校验、启动 spec、重启沿用、并发排队、启动失败、crash-watch，以及控制面的 PreviewStarter。

状态分活着和能服务两档，crash-watch 只认前者。这一组里最该守住的是「活着但答不出的进程不会被
重启」：把就绪当健康，正好会在应用启动最慢的时候把它停掉。
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import pytest

from app_spark_agent import settings
from app_spark_agent.app_arch.app_desc import render_app_desc
from app_spark_agent.app_arch.files import AppArchErrorCode, FileSyncResult, FileSyncStatus
from app_spark_agent.app_arch.python import APP_IMPORT_PATH, PYTHON_VERSION
from app_spark_agent.app_supervisor import (
    APP_PORT_ENV,
    LAUNCH_EVENT_RUN_ID,
    AppLaunchConflict,
    AppLaunchFailed,
    AppSupervisor,
    DevServerStatus,
    PreviewStarter,
    build_app_spec,
    build_child_environ,
)
from app_spark_agent.app_supervisor import process as process_mod
from app_spark_agent.app_supervisor import supervisor as supervisor_mod
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
    """假端口 + 假进程。两个开关分别对应「进程活不活」和「端口答不答」，因为这两件事要分开验。

    auto_listen 关掉后 spawn 不再把端口标成在听；spawns_living 关掉后拉起来的子进程当场就是死的。
    """

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
        self.spawns_living = living
        self.spawned: list[Child] = []
        self._fail_on = fail_on
        self._calls = 0
        (tmp_path / "workspace").mkdir(exist_ok=True)
        (tmp_path / "workspace" / "pyproject.toml").write_text("# the project\n")

        # 依赖对齐也假掉：真 uv 由 test_project_env.py 验。这里只记下每次对齐时已经拉起过几个
        # 子进程，好断言「先装依赖、再 spawn」；sync_error 不为空时就按它失败。
        self.synced_after_spawns: list[int] = []
        self.python_versions_at_sync: list[str] = []
        self.sync_error: AppLaunchFailed | None = None
        # 设了就停在依赖对齐里，直到测试放行：用来看 spawn 之前那段的状态。
        self.sync_gate: asyncio.Event | None = None

        async def sync(workspace: Path, _log_path: Path) -> None:
            self.synced_after_spawns.append(len(self.spawned))
            self.python_versions_at_sync.append((workspace / ".python-version").read_text())
            if self.sync_gate is not None:
                await self.sync_gate.wait()
            if self.sync_error is not None:
                raise self.sync_error

        async def answers(_port: int) -> bool:
            return self.listening

        monkeypatch.setattr(supervisor_mod, "sync_project_environment", sync)

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
        child = Child(living=self.spawns_living)
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
    # 生产是 30s / 2s / 0.5s / 5s，单测不能真睡那么久。假进程停掉后端口不会自己放开，重启总要等满最后一个。
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.4)
    monkeypatch.setattr(supervisor_mod, "PORT_FREE_TIMEOUT_SECONDS", 0.1)
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

    env = build_child_environ(Path("/data/workspace"), 8123, source)

    assert all(key not in env for key in secrets)
    # 不是密钥，一样不给。应用的 cwd 就是 workspace。
    assert "APP_SPARK_AGENT_WORKSPACE" not in env
    # 唯一加回来的一项，尽管它也带前缀。
    assert env[APP_PORT_ENV] == "8123"


def test_child_env_activates_the_projects_venv_instead_of_the_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """应用按命令名跑 python / pip 时，进的得是项目环境，pip install 也不能改到 Agent 自己的包。"""
    monkeypatch.setattr(sys, "prefix", "/app/.venv")
    monkeypatch.setattr(sys, "base_prefix", "/usr/local")
    source = {
        "PATH": os.pathsep.join(("/app/.venv/bin", "/usr/local/bin", "/usr/bin")),
        "VIRTUAL_ENV": "/app/.venv",
        "UV_PROJECT_ENVIRONMENT": "/app/.venv",
    }

    env = build_child_environ(Path("/data/workspace"), 8123, source)

    assert env["PATH"] == os.pathsep.join(("/data/workspace/.venv/bin", "/usr/local/bin", "/usr/bin"))
    assert env["VIRTUAL_ENV"] == "/data/workspace/.venv"
    assert "UV_PROJECT_ENVIRONMENT" not in env


def test_child_env_without_path_still_finds_system_commands() -> None:
    env = build_child_environ(Path("/data/workspace"), 8123, {})

    assert env["PATH"] == os.pathsep.join(("/data/workspace/.venv/bin", os.defpath))


def test_spec_starts_the_import_path_the_instructions_promise(tmp_path: Path) -> None:
    """启动命令和提示词里的入口名是一对，改一边就必须改另一边，否则 launch 必失败。"""
    spec = build_app_spec(tmp_path, 8123)

    assert APP_IMPORT_PATH in spec.argv
    assert APP_IMPORT_PATH in settings.INSTRUCTIONS
    assert spec.argv[-2:] == ("--port", "8123")
    assert spec.cwd == tmp_path


def test_spec_runs_the_projects_own_interpreter(tmp_path: Path) -> None:
    assert build_app_spec(tmp_path, 8123).argv[0] == str(tmp_path / ".venv" / "bin" / "python")


async def test_launch_repairs_platform_configuration_before_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = App(monkeypatch, tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "app_desc.yaml").write_text("stale\n")

    await app.supervisor.restart()

    assert (workspace / "app_desc.yaml").read_text() == render_app_desc()
    assert (workspace / ".python-version").read_text() == f"{PYTHON_VERSION}\n"
    assert len(app.spawned) == 1


async def test_launch_repairs_the_python_version_before_uv_reads_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale .python-version makes uv sync fail first, so repairing it afterwards would never run."""
    app = App(monkeypatch, tmp_path)
    (tmp_path / "workspace" / ".python-version").write_text("3.13\n")

    await app.supervisor.restart()

    assert app.python_versions_at_sync == [f"{PYTHON_VERSION}\n"]


async def test_platform_configuration_write_failure_prevents_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_sync(*_args: object) -> FileSyncResult:
        return FileSyncResult(
            status=FileSyncStatus.FAILED,
            errcode=AppArchErrorCode.WRITE_FAILED,
            detail="Could not synchronize app_desc.yaml: disk full",
        )

    monkeypatch.setattr(supervisor_mod.AppArchitecture, "sync", fail_sync)
    app = App(monkeypatch, tmp_path)

    with pytest.raises(AppLaunchFailed, match=r"platform configuration.*disk full"):
        await app.supervisor.restart()

    assert app.synced_after_spawns == []
    assert app.spawned == []


async def test_a_launch_without_a_project_does_not_create_platform_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = App(monkeypatch, tmp_path)
    (tmp_path / "workspace" / "pyproject.toml").unlink()

    with pytest.raises(AppLaunchFailed, match="no pyproject"):
        await app.supervisor.restart()

    assert list((tmp_path / "workspace").iterdir()) == []
    assert app.synced_after_spawns == []
    assert app.spawned == []


async def test_a_failed_install_fails_the_launch_without_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """依赖装不上就别拉：拿缺包的环境起应用，只会把原因换成一个更难读的 ImportError。"""
    app = App(monkeypatch, tmp_path)
    app.sync_error = AppLaunchFailed("Installing the project's dependencies failed")

    with pytest.raises(AppLaunchFailed, match="dependencies failed"):
        await app.supervisor.restart()
    assert app.spawned == []
    assert await app.supervisor.dev_server_status() is DevServerStatus.NOT_STARTED


async def test_a_spawn_error_is_reported_as_a_launch_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """launch_app 只把 AppLaunchError 交回模型，裸 OSError 会掐断整轮。"""
    app = App(monkeypatch, tmp_path, fail_on=1)

    with pytest.raises(AppLaunchFailed, match="spawn refused"):
        await app.supervisor.restart()


async def test_relaunch_replaces_the_process_and_reuses_the_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = App(monkeypatch, tmp_path)
    first = await app.supervisor.restart()
    app.listening = False

    second = await app.supervisor.restart()

    assert (first.path, first.label) == (second.path, second.label) == ("/", "Preview")
    assert len(app.spawned) == 2
    # 旧进程必须真的被换掉，否则「再次 launch 加载新代码」这条就不成立。
    assert app.spawned[0].poll() is not None
    # 固定哨兵，不是每次 launch 灌一个新 uuid 进 AppendLog._run_ids。
    assert app.run_ids() == {LAUNCH_EVENT_RUN_ID}


async def test_a_second_restart_waits_for_the_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """排队而不是冲突：第二次照样重启，加载的是它那一刻的代码。"""
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    first = asyncio.create_task(app.supervisor.restart())
    await wait_until(lambda: len(app.synced_after_spawns) == 1)
    second = asyncio.create_task(app.supervisor.restart())
    await asyncio.sleep(0.05)
    assert app.spawned == []

    app.sync_gate.set()
    assert (await first).dev_server_status == DevServerStatus.READY
    assert (await second).dev_server_status == DevServerStatus.READY
    assert len(app.spawned) == 2
    assert app.spawned[0].poll() is not None


async def test_a_process_that_exits_before_listening_fails_the_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """进程没能活下来才算 launch 失败。没有进程就没什么可等的，模型该去读日志。"""
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.15)
    app = App(monkeypatch, tmp_path, living=False, auto_listen=False)

    with pytest.raises(AppLaunchFailed, match="exited before it listened"):
        await app.supervisor.restart()

    assert await app.supervisor.dev_server_status() == DevServerStatus.STOPPED


async def test_a_launch_that_times_out_leaves_the_live_process_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """等不到应答不算失败，也不停进程：慢启动被杀掉，正是把就绪当健康的那个错。"""
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.1)
    app = App(monkeypatch, tmp_path, auto_listen=False)

    result = await app.supervisor.restart()

    assert result.dev_server_status == DevServerStatus.STARTING
    assert app.spawned[-1].poll() is None

    # 之后应用自己听上了，不必再 launch 一次：状态是现算的。
    app.listening = True
    assert await app.supervisor.dev_server_status() == DevServerStatus.READY


async def test_watch_restarts_after_a_spawn_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # fail_on=2：第一次手动 launch 成功，自动重启第一次抛 OSError，第二次拉起来。
    app = App(monkeypatch, tmp_path, fail_on=2)
    await app.supervisor.restart()
    app.drop()
    async with watching(app.supervisor) as task:
        await wait_until(lambda: len(app.spawned) == 2)
        assert not task.done()
        assert await app.supervisor.dev_server_status() == DevServerStatus.READY
        assert app.run_ids() == {LAUNCH_EVENT_RUN_ID}


async def test_watch_leaves_a_live_process_that_cannot_answer_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """这一条是 crash-watch 判活不判就绪的全部意义。

    进程在跑，只是答不出 HTTP：可能在跑启动钩子，也可能首屏慢过探针的读预算。停掉重拉救不了它，
    只会把一个正在预热的应用打断，让「慢」变成「永远起不来」。
    """
    app = App(monkeypatch, tmp_path)
    await app.supervisor.restart()
    app.listening = False

    async with watching(app.supervisor):
        # 轮询间隔被压到 10ms，这段时间够转很多圈。
        await asyncio.sleep(0.15)

        assert len(app.spawned) == 1
        assert app.spawned[0].poll() is None
        assert await app.supervisor.dev_server_status() == DevServerStatus.STARTING


async def test_watch_gives_up_after_retry_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor_mod, "LISTEN_TIMEOUT_SECONDS", 0.08)
    monkeypatch.setattr(supervisor_mod, "CRASH_RETRY_LIMIT", 2)
    app = App(monkeypatch, tmp_path)
    await app.supervisor.restart()

    # 之后拉起来的都活不下来，否则 watch 看到一个活进程就不再重试，额度永远用不完。
    app.spawns_living = False
    app.auto_listen = False
    app.drop()

    async with watching(app.supervisor):
        await wait_until(lambda: app.supervisor._auto_restarts >= 2, timeout=2.0)
        assert await app.supervisor.dev_server_status() == DevServerStatus.STOPPED
        stopped_at = len(app.spawned)
        await asyncio.sleep(0.1)
        assert len(app.spawned) == stopped_at


async def test_watch_ignores_never_launched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path, auto_listen=False)
    async with watching(app.supervisor):
        await asyncio.sleep(0.08)
        assert app.spawned == []
        assert await app.supervisor.dev_server_status() == DevServerStatus.NOT_STARTED


async def test_start_brings_the_app_up_in_the_background(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """控制面不等：装依赖可能要几分钟，那段时间状态得是 starting，而不是 not_started。"""
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    starter = PreviewStarter(app.supervisor)

    starter.start()
    await wait_until(lambda: len(app.synced_after_spawns) == 1)
    assert await app.supervisor.dev_server_status() is DevServerStatus.STARTING
    assert app.spawned == []

    app.sync_gate.set()
    await wait_until(lambda: len(app.run_ids()) == 1)
    assert await app.supervisor.dev_server_status() is DevServerStatus.READY
    assert app.run_ids() == {LAUNCH_EVENT_RUN_ID}


async def test_start_leaves_a_live_process_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """用户打开页面不是重启的理由：重启加载新代码是模型 launch 的事。"""
    app = App(monkeypatch, tmp_path)
    await app.supervisor.restart()
    app.listening = False

    PreviewStarter(app.supervisor).start()
    await asyncio.sleep(0.05)
    assert len(app.spawned) == 1
    assert app.spawned[0].poll() is None
    assert len(app.synced_after_spawns) == 1


async def test_start_twice_starts_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    starter = PreviewStarter(app.supervisor)

    starter.start()
    starter.start()
    await wait_until(lambda: len(app.synced_after_spawns) == 1)
    starter.start()

    app.sync_gate.set()
    await wait_until(lambda: len(app.run_ids()) == 1)
    await asyncio.sleep(0.05)
    assert len(app.spawned) == 1
    assert len(app.synced_after_spawns) == 1


async def test_start_during_a_restart_does_not_spawn_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """模型正在 launch 时控制面来 start：等那次结束，看到进程活着就不动。"""
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    restart = asyncio.create_task(app.supervisor.restart())
    await wait_until(lambda: len(app.synced_after_spawns) == 1)

    PreviewStarter(app.supervisor).start()

    app.sync_gate.set()
    await restart
    await asyncio.sleep(0.05)
    assert len(app.spawned) == 1


async def test_a_restart_waits_for_a_start_in_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """用户刚进旧项目就发消息：模型的 launch 不该因为控制面正在装依赖而算一次失败。"""
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    PreviewStarter(app.supervisor).start()
    await wait_until(lambda: len(app.synced_after_spawns) == 1)

    restart = asyncio.create_task(app.supervisor.restart())
    await asyncio.sleep(0.05)
    app.sync_gate.set()

    assert (await restart).dev_server_status is DevServerStatus.READY
    assert len(app.spawned) == 2
    assert app.spawned[0].poll() is not None


async def test_start_without_a_project_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path)
    (tmp_path / "workspace" / "pyproject.toml").unlink()

    with pytest.raises(AppLaunchFailed, match="no pyproject"):
        PreviewStarter(app.supervisor).start()
    await asyncio.sleep(0.05)
    assert app.synced_after_spawns == []
    assert list((tmp_path / "workspace").iterdir()) == []


async def test_start_refuses_a_foreign_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path)
    app.listening = True

    with pytest.raises(AppLaunchConflict, match="did not start"):
        PreviewStarter(app.supervisor).start()
    assert await app.supervisor.dev_server_status() is DevServerStatus.NOT_STARTED


async def test_start_during_a_restart_does_not_mistake_our_old_port_for_a_foreign_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """restart 停掉旧进程、端口还没放开时，占着端口的是我们自己的进程。"""
    monkeypatch.setattr(supervisor_mod, "PORT_FREE_TIMEOUT_SECONDS", 1.0)
    app = App(monkeypatch, tmp_path)
    await app.supervisor.restart()

    # 假进程停掉后端口不会自己放开：restart 停在等端口这一步。
    restart = asyncio.create_task(app.supervisor.restart())
    await asyncio.sleep(0.05)
    assert app.spawned[0].poll() is not None
    assert app.listening

    PreviewStarter(app.supervisor).start()

    app.listening = False
    assert (await restart).dev_server_status is DevServerStatus.READY
    await asyncio.sleep(0.05)
    assert len(app.spawned) == 2


async def test_a_failed_start_falls_back_from_starting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """没人等着接异常，调用方只能从状态回落看出失败了，所以 starting 不能卡住不动。"""
    app = App(monkeypatch, tmp_path)
    app.sync_error = AppLaunchFailed("Installing the project's dependencies failed")
    starter = PreviewStarter(app.supervisor)

    starter.start()
    await wait_until(lambda: len(app.synced_after_spawns) == 1)
    await asyncio.sleep(0.05)

    assert await app.supervisor.dev_server_status() is DevServerStatus.NOT_STARTED
    assert app.spawned == []
    assert app.run_ids() == set()

    # 失败之后还能再来。
    app.sync_error = None
    starter.start()
    await wait_until(lambda: len(app.run_ids()) == 1)
    assert await app.supervisor.dev_server_status() is DevServerStatus.READY


async def test_aclose_cancels_a_start_in_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = App(monkeypatch, tmp_path)
    app.sync_gate = asyncio.Event()
    starter = PreviewStarter(app.supervisor)
    starter.start()
    await wait_until(lambda: len(app.synced_after_spawns) == 1)

    await starter.aclose()

    assert app.spawned == []
    assert await app.supervisor.dev_server_status() is DevServerStatus.NOT_STARTED


async def test_a_restart_reports_starting_while_installing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """模型 launch 也一样：重启时旧进程已停、新进程还没 spawn，这段不是 stopped。"""
    app = App(monkeypatch, tmp_path)
    await app.supervisor.restart()
    app.listening = False
    app.sync_gate = asyncio.Event()
    relaunch = asyncio.create_task(app.supervisor.restart())
    await wait_until(lambda: len(app.synced_after_spawns) == 2)

    assert await app.supervisor.dev_server_status() is DevServerStatus.STARTING

    app.sync_gate.set()
    assert (await relaunch).dev_server_status is DevServerStatus.READY
