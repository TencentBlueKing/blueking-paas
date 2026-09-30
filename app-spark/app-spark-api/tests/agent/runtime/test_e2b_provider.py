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

"""Races and injected failures the live E2B suite cannot stage.

``test_e2b_integration.py`` already drives a real sandbox through create, reuse, preview,
busy projects, shutdown, and expiry. What it cannot do on demand is fail at a chosen moment,
move the clock past an abandoned claim, or hold one create open while another request runs.
A second provider instance stands in for another API worker: it shares nothing with the first
but the database, exactly like a worker in another process.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import attrs
import pytest
from django.utils import timezone
from e2b import AsyncSandbox, NotFoundException, SandboxException

from app_spark_api.agent.runtime.constants import ENV_PREFIX
from app_spark_api.agent.runtime.entities import (
    AgentRuntimeHandle,
    DirectModelAccess,
    E2BConfig,
    GitRemote,
    ModelAccess,
    StateCallback,
)
from app_spark_api.agent.runtime.exceptions import (
    AgentProvisionError,
    AgentWorkspaceBusyError,
    ModelCredentialMissingError,
)
from app_spark_api.agent.runtime.models import E2BSandboxRecord
from app_spark_api.agent.runtime.providers import e2b as e2b_module
from app_spark_api.agent.runtime.providers.e2b import ABANDONED_CLAIM_SECONDS, E2BProvider, _SandboxClaim

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

pytestmark = pytest.mark.django_db(transaction=True)

CONFIG = E2BConfig(
    api_key="e2b-key",
    api_url="https://e2b.example",
    callback_base_url="https://app-spark.example",
    domain="sandbox.example",
)

AGENT_LOG = "Traceback (most recent call last):\nValueError: the agent refused its configuration"


async def resolve_direct_access() -> ModelAccess:
    """Model access that needs no token exchange."""
    return DirectModelAccess(model="fake:write-file")


class DefaultAccessProvider(E2BProvider):
    """The real provider, except that callers here need not repeat the model access every time."""

    async def ensure(self, *, model_access: Any = resolve_direct_access, **kwargs: Any) -> AgentRuntimeHandle:  # type: ignore[override]
        return await super().ensure(model_access=model_access, **kwargs)


class FakeProcess:
    """The part of ``AsyncCommandHandle`` the provider touches."""

    def __init__(self, pid: int, exit_code: int | None, stderr: str) -> None:
        self.pid = pid
        self.exit_code = exit_code
        self.stdout = ""
        self.stderr = stderr
        self.disconnected = False

    async def disconnect(self) -> None:
        self.disconnected = True


class FakeCommands:
    """Records what the provider starts in the sandbox."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.processes: list[FakeProcess] = []
        # Staged before the provider starts the Agent: a start refused by envd, or an Agent that
        # has already exited by the time the provider first looks.
        self.run_error: Exception | None = None
        self.exit_code: int | None = None
        # What the shell itself printed, e.g. before it could open the log file.
        self.stderr = ""

    async def run(self, cmd: str, **opts: Any) -> FakeProcess:
        if self.run_error is not None:
            raise self.run_error
        self.calls.append({"cmd": cmd, **opts})
        process = FakeProcess(pid=4200 + len(self.calls), exit_code=self.exit_code, stderr=self.stderr)
        self.processes.append(process)
        return process


class FakeFiles:
    """Serves the Agent's log from the sandbox it belongs to."""

    def __init__(self, sandbox: FakeSandbox) -> None:
        self.sandbox = sandbox

    async def read(self, path: str, **_opts: object) -> str:
        if self.sandbox.agent_log is None:
            raise NotFoundException(path)
        return self.sandbox.agent_log


class FakeSandbox:
    """The part of ``AsyncSandbox`` the provider touches, with switches to make it fail."""

    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        self.sandbox_domain = "sandbox.example"
        self.traffic_access_token = f"traffic-{sandbox_id}"
        self.connection_config = SimpleNamespace(sandbox_headers={"X-Access-Token": f"envd-{sandbox_id}"})
        self.killed = False
        self.info_error: Exception | None = None
        self.kill_error: Exception | None = None
        self.commands = FakeCommands()
        self.files = FakeFiles(self)
        self.agent_log: str | None = None

    async def get_info(self) -> SimpleNamespace:
        if self.info_error is not None:
            raise self.info_error
        return SimpleNamespace(sandbox_domain=self.sandbox_domain, envd_version="0.2.0")

    async def is_running(self) -> bool:
        return not self.killed

    async def kill(self) -> None:
        if self.kill_error is not None:
            raise self.kill_error
        self.killed = True

    def get_host(self, port: int) -> str:
        return f"{port}-{self.sandbox_id}.{self.sandbox_domain}"


class FakeE2B:
    """Stands in for the control plane behind ``AsyncSandbox.create`` and ``connect``."""

    def __init__(self) -> None:
        self.sandboxes: dict[str, FakeSandbox] = {}
        self.create_calls = 0
        self.create_opts: list[dict[str, object]] = []
        self.connect_calls = 0
        self.create_started = asyncio.Event()
        self.create_error: Exception | None = None
        self.connect_error: Exception | None = None
        # Runs inside `create` before it answers, which is where a race or a failure is staged.
        self.on_create: Callable[[int], Awaitable[None]] | None = None
        # Applied to each sandbox before it is handed back, to stage a failure after creation.
        self.prepare: Callable[[FakeSandbox], None] | None = None

    async def create(self, template: str, **opts: object) -> FakeSandbox:
        self.create_calls += 1
        self.create_opts.append(opts)
        self.create_started.set()
        call = self.create_calls
        if self.on_create is not None:
            await self.on_create(call)
        if self.create_error is not None:
            raise self.create_error
        sandbox = FakeSandbox(f"sbx-{call}")
        if self.prepare is not None:
            self.prepare(sandbox)
        self.sandboxes[sandbox.sandbox_id] = sandbox
        return sandbox

    async def connect(self, sandbox_id: str, **_opts: object) -> FakeSandbox:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        try:
            return self.sandboxes[sandbox_id]
        except KeyError:
            raise NotFoundException(sandbox_id) from None


@pytest.fixture
def e2b(monkeypatch) -> FakeE2B:
    fake = FakeE2B()
    monkeypatch.setattr(AsyncSandbox, "create", staticmethod(fake.create))
    monkeypatch.setattr(AsyncSandbox, "connect", staticmethod(fake.connect))
    return fake


@pytest.fixture(autouse=True)
def agent_health(monkeypatch) -> SimpleNamespace:
    """Answer the provider's /health probes without a network; healthy unless a test says not."""
    state = SimpleNamespace(healthy=True, probes=0, probing=asyncio.Event())

    async def probe(_handle: AgentRuntimeHandle, **_opts: object) -> bool:
        state.probes += 1
        state.probing.set()
        return state.healthy

    monkeypatch.setattr(e2b_module, "probe_agent_health", probe)
    monkeypatch.setattr(e2b_module, "HEALTH_POLL_INTERVAL_SECONDS", 0.01)
    return state


@pytest.fixture
def provider() -> E2BProvider:
    return DefaultAccessProvider(CONFIG)


@pytest.fixture
def other_worker() -> E2BProvider:
    """A provider that shares only the database with ``provider``, like a second API worker."""
    return DefaultAccessProvider(CONFIG)


def ids() -> tuple[str, str]:
    return str(uuid4()), str(uuid4())


async def create_started(e2b: FakeE2B) -> None:
    """Wait until another task has claimed and reached E2B; the claim goes through a DB thread."""
    await asyncio.wait_for(e2b.create_started.wait(), timeout=5)


async def wait_until_probing(agent_health: SimpleNamespace) -> None:
    """Wait until another task has bound its sandbox and is polling the Agent's /health."""
    await asyncio.wait_for(agent_health.probing.wait(), timeout=5)


# --- 先占位，再建沙箱 ----------------------------------------------------------------------


async def test_conversations_do_not_wait_behind_each_other(e2b, provider):
    """锁按会话分：一个会话卡在建沙箱上，别的会话照常。"""
    released = asyncio.Event()

    async def stall_first(call: int) -> None:
        if call == 1:
            await released.wait()

    e2b.on_create = stall_first
    stalled = asyncio.create_task(provider.ensure(project_id=str(uuid4()), conversation_id=str(uuid4())))
    try:
        await create_started(e2b)

        await asyncio.wait_for(provider.ensure(project_id=str(uuid4()), conversation_id=str(uuid4())), timeout=5)
    finally:
        released.set()
        await stalled


async def test_two_workers_racing_for_one_conversation_create_one_sandbox(e2b, provider, other_worker):
    """两个 worker 谁先占到位谁建，输的那个一个沙箱都没建过，也就没有要回收的东西。"""
    project_id, conversation_id = ids()

    async def slow_create(_call: int) -> None:
        await asyncio.sleep(0.05)

    e2b.on_create = slow_create
    outcomes = await asyncio.gather(
        provider.ensure(project_id=project_id, conversation_id=conversation_id),
        other_worker.ensure(project_id=project_id, conversation_id=conversation_id),
        return_exceptions=True,
    )

    assert sorted(type(outcome).__name__ for outcome in outcomes) == ["AgentRuntimeHandle", "AgentWorkspaceBusyError"]
    assert e2b.create_calls == 1
    assert not any(sandbox.killed for sandbox in e2b.sandboxes.values())


async def test_a_claim_in_progress_is_busy_until_it_is_old_enough_to_be_abandoned(e2b, provider):
    """另一个 worker 正在建的占位要等；它死在半路留下的占位不能永远占着 Project。"""
    project_id, conversation_id = ids()
    orphan = await E2BSandboxRecord.objects.acreate(
        project_id=project_id,
        conversation_id="elsewhere",
        active_project_id=project_id,
        active_conversation_id="elsewhere",
        runtime_token="token",
        template=CONFIG.template,
    )

    with pytest.raises(AgentWorkspaceBusyError):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    assert e2b.create_calls == 0

    await E2BSandboxRecord.objects.filter(pk=orphan.pk).aupdate(
        created_at=timezone.now() - timedelta(seconds=ABANDONED_CLAIM_SECONDS + 1)
    )
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    await orphan.arefresh_from_db()
    assert (orphan.active_project_id, orphan.stop_reason) == (None, "abandoned")


async def test_a_stale_abandoned_view_does_not_release_a_sandbox_bound_since(e2b, provider):
    """读到「还没绑定」之后沙箱已经绑上了，不能按 abandoned 把活记录放掉。"""
    project_id, conversation_id = ids()
    stale: dict[str, E2BSandboxRecord] = {}

    async def remember_the_unbound_claim(_call: int) -> None:
        stale["record"] = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)

    e2b.on_create = remember_the_unbound_claim
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    # The in-memory row is what a concurrent ensure loaded before the bind landed, and it is
    # old enough that the abandoned check would otherwise give the claim away.
    stale["record"].created_at = timezone.now() - timedelta(seconds=ABANDONED_CLAIM_SECONDS + 1)

    assert await _SandboxClaim(stale["record"], provider.config).connect(reconcile=True) is not None

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (conversation_id, "sbx-1", "")
    assert not e2b.sandboxes["sbx-1"].killed


# --- 失败时交还占位 --------------------------------------------------------------------------


async def test_a_failed_create_gives_its_claim_back(e2b, provider):
    project_id, conversation_id = ids()
    e2b.create_error = SandboxException("quota exceeded")

    with pytest.raises(AgentProvisionError, match="quota exceeded"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, None, "failed")

    e2b.create_error = None
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)


async def test_a_cleanup_failure_does_not_replace_the_provisioning_error(e2b, provider):
    """清理是尽力而为：kill 失败只记日志，调用方看到的仍是原本那个错，占位也照样交还。"""
    project_id, conversation_id = ids()

    def break_after_creation(sandbox: FakeSandbox) -> None:
        sandbox.info_error = SandboxException("envd unreachable")
        sandbox.kill_error = SandboxException("kill refused")

    e2b.prepare = break_after_creation

    with pytest.raises(AgentProvisionError, match="envd unreachable"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert not await E2BSandboxRecord.objects.active_for_project(project_id).aexists()


async def test_a_claim_released_during_creation_takes_the_new_sandbox_down(e2b, provider, other_worker):
    """建沙箱那几秒里，另一个 worker 结束了这个会话。新沙箱不能挂在一条已经释放的记录上。"""
    project_id, conversation_id = ids()

    async def terminate_meanwhile(_call: int) -> None:
        await other_worker.terminate(conversation_id)

    e2b.on_create = terminate_meanwhile

    with pytest.raises(AgentProvisionError, match="released"):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, None, "terminated")


async def test_terminating_a_claim_bound_since_it_was_read_still_kills_the_sandbox(e2b, provider, other_worker):
    """terminate 读到未绑定的占位时，绑定可能已经落库。放掉记录的同时必须把那个沙箱杀掉。"""
    project_id, conversation_id = ids()
    stale: dict[str, E2BSandboxRecord] = {}

    async def remember_the_unbound_claim(_call: int) -> None:
        stale["record"] = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)

    e2b.on_create = remember_the_unbound_claim
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    assert stale["record"].sandbox_id is None

    await _SandboxClaim(stale["record"], other_worker.config).terminate()

    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.sandbox_id, record.stop_reason) == (None, "sbx-1", "terminated")


async def test_a_cancelled_provisioning_gives_its_claim_back(e2b, provider):
    """请求被断开时 ensure 被取消，占位不能留到被当成 abandoned 才放出来。"""
    project_id, conversation_id = ids()
    never = asyncio.Event()

    async def hang(_call: int) -> None:
        await never.wait()

    e2b.on_create = hang
    task = asyncio.create_task(provider.ensure(project_id=project_id, conversation_id=conversation_id))
    await create_started(e2b)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.stop_reason) == (None, "failed")


# --- 看一眼没有副作用 ------------------------------------------------------------------------


async def test_a_control_plane_hiccup_while_looking_does_not_release_the_sandbox(e2b, provider):
    """状态轮询时控制面抛错，不能把一条还占着的记录放掉。"""
    project_id, conversation_id = ids()
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    e2b.connect_error = SandboxException("control plane hiccup")

    with pytest.raises(AgentProvisionError, match="control plane hiccup"):
        await provider.peek(conversation_id)

    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.stop_reason) == (conversation_id, "")


async def test_the_preview_target_does_not_ask_e2b(e2b, provider):
    """预览页的每个静态资源都会走这里。集成测试对得上真实地址，这里只证明这一步不再请求 E2B。"""
    project_id, conversation_id = ids()
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    e2b.connect_calls = 0

    target = await provider.preview_target(conversation_id)

    assert target is not None
    assert target.http_headers == {
        "X-Access-Token": "envd-sbx-1",
        "E2B-Traffic-Access-Token": "traffic-sbx-1",
    }
    assert e2b.connect_calls == 0


async def test_an_unbound_claim_has_nothing_to_preview_or_peek_at(e2b, provider):
    project_id, conversation_id = ids()
    await E2BSandboxRecord.objects.acreate(
        project_id=project_id,
        conversation_id=conversation_id,
        active_project_id=project_id,
        active_conversation_id=conversation_id,
        runtime_token="token",
        template=CONFIG.template,
    )

    assert await provider.preview_target(conversation_id) is None
    assert await provider.peek(conversation_id) is None
    assert e2b.connect_calls == 0


# --- 在沙箱里启动 Agent ----------------------------------------------------------------------

STATE_CALLBACK = StateCallback(path="/api-svc/api/internal/conversations/c-1/state/", token="state-token")
GIT_REMOTE = GitRemote(
    clone_url="https://git.example/app-spark/p.git", branch="main", username="app-spark-bot", token="repo-token"
)


async def test_the_agent_is_started_with_its_whole_configuration(e2b, provider):
    """端口两个都显式给；回写地址保留公开前缀，因为沙箱是经 Ingress 回调进来的。"""
    project_id, conversation_id = ids()

    handle = await provider.ensure(
        project_id=project_id,
        conversation_id=conversation_id,
        state_callback=STATE_CALLBACK,
        git_remote=GIT_REMOTE,
    )

    (call,) = e2b.sandboxes["sbx-1"].commands.calls
    envs = call["envs"]
    assert (call["background"], call["timeout"]) == (True, 0)
    assert call["cmd"] == (
        "{ mkdir -p /data/workspace /data && exec python -m app_spark_agent; } >> /tmp/app-spark-agent.log 2>&1"
    )
    # Credentials go to this one process through envd, never through the sandbox's creation.
    (create_opts,) = e2b.create_opts
    assert not {"envs", "env_vars", "metadata"} & set(create_opts)
    assert envs[f"{ENV_PREFIX}PORT"] == str(CONFIG.runtime_port)
    assert envs[f"{ENV_PREFIX}APP_PORT"] == str(CONFIG.preview_port)
    assert envs[f"{ENV_PREFIX}WORKSPACE"] == "/data/workspace"
    assert envs[f"{ENV_PREFIX}STATE_DIR"] == "/data/state"
    assert envs[f"{ENV_PREFIX}PROJECT_ID"] == project_id
    assert envs[f"{ENV_PREFIX}RUNTIME_TOKEN"] == handle.runtime_token
    assert envs[f"{ENV_PREFIX}CONTROL_PLANE_URL"] == f"https://app-spark.example{STATE_CALLBACK.path}"
    assert envs[f"{ENV_PREFIX}CONTROL_PLANE_TOKEN"] == "state-token"
    assert envs[f"{ENV_PREFIX}GIT_REMOTE_URL"] == GIT_REMOTE.clone_url
    assert envs[f"{ENV_PREFIX}GIT_TOKEN"] == "repo-token"
    assert envs[f"{ENV_PREFIX}MODEL"] == "fake:write-file"
    # Nothing of this service's own environment, unlike the local provider's allow-listed part.
    assert all(name.startswith(ENV_PREFIX) for name in envs)

    # The pid is written only once the Agent answered, and the start's event stream is let go.
    (process,) = e2b.sandboxes["sbx-1"].commands.processes
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert record.agent_pid == process.pid
    assert process.disconnected


async def test_extra_env_extends_the_agent_but_cannot_replace_its_identity(e2b):
    config = attrs.evolve(
        CONFIG,
        extra_env={f"{ENV_PREFIX}RUNTIME_TOKEN": "forged", f"{ENV_PREFIX}FAKE_DELAY_SECONDS": "1"},
    )

    handle = await DefaultAccessProvider(config).ensure(project_id=str(uuid4()), conversation_id=str(uuid4()))

    envs = e2b.sandboxes["sbx-1"].commands.calls[0]["envs"]
    assert envs[f"{ENV_PREFIX}RUNTIME_TOKEN"] == handle.runtime_token
    assert envs[f"{ENV_PREFIX}FAKE_DELAY_SECONDS"] == "1"


async def test_a_running_runtime_costs_no_token_exchange(e2b, provider):
    """已在跑的 Runtime 不再换票：换票只发生在真要新起的时候。"""
    project_id, conversation_id = ids()
    exchanges = 0

    async def count_exchanges() -> ModelAccess:
        nonlocal exchanges
        exchanges += 1
        return DirectModelAccess(model="fake:write-file")

    first = await provider.ensure(project_id=project_id, conversation_id=conversation_id, model_access=count_exchanges)
    second = await provider.ensure(
        project_id=project_id, conversation_id=conversation_id, model_access=count_exchanges
    )

    assert first == second
    assert exchanges == 1
    assert e2b.create_calls == 1
    assert len(e2b.sandboxes["sbx-1"].commands.calls) == 1


async def test_a_failed_token_exchange_creates_no_sandbox(e2b, provider):
    """先换票再占位：换票失败时既没有沙箱，也没有占位要收拾。"""
    project_id, conversation_id = ids()

    async def refuse() -> ModelAccess:
        raise ModelCredentialMissingError("no login")

    with pytest.raises(ModelCredentialMissingError):
        await provider.ensure(project_id=project_id, conversation_id=conversation_id, model_access=refuse)

    assert e2b.create_calls == 0
    assert not await E2BSandboxRecord.objects.filter(conversation_id=conversation_id).aexists()


def exit_with_a_traceback(sandbox: FakeSandbox) -> None:
    sandbox.commands.exit_code = 1
    sandbox.agent_log = AGENT_LOG


def exit_before_the_log_opens(sandbox: FakeSandbox) -> None:
    sandbox.commands.exit_code = 1
    sandbox.commands.stderr = "bash: /data/app-spark-agent.log: Permission denied"


def refuse_to_start(sandbox: FakeSandbox) -> None:
    sandbox.commands.run_error = SandboxException("envd refused the process")


@pytest.mark.parametrize(
    ("stage_failure", "startup_timeout", "expected"),
    [
        # A bad configuration kills the Agent during import; its own traceback says why.
        pytest.param(
            exit_with_a_traceback, 60.0, ("exited during startup with code 1", "refused its configuration"), id="exits"
        ),
        # The shell could not even open the log, so the reason is in the command's own output.
        pytest.param(exit_before_the_log_opens, 60.0, ("exited during startup", "Permission denied"), id="no-log"),
        pytest.param(None, 0.05, ("never became healthy", "wrote no output"), id="never-answers"),
        pytest.param(
            refuse_to_start, 60.0, ("Could not start the Agent", "envd refused the process"), id="envd-refuses"
        ),
    ],
)
async def test_a_failed_start_is_explained_and_gives_its_sandbox_back(
    e2b, agent_health, stage_failure, startup_timeout, expected
):
    project_id, conversation_id = ids()
    message, detail = expected
    agent_health.healthy = False
    e2b.prepare = stage_failure
    provider = DefaultAccessProvider(attrs.evolve(CONFIG, startup_timeout_seconds=startup_timeout))

    with pytest.raises(AgentProvisionError, match=message) as exc_info:
        await provider.ensure(project_id=project_id, conversation_id=conversation_id)

    assert detail in str(exc_info.value)
    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.agent_pid, record.stop_reason) == (None, None, "failed")


# --- 启动中的沙箱不交出去 ----------------------------------------------------------------------


async def test_a_sandbox_still_starting_its_agent_is_not_handed_out(e2b, provider, other_worker, agent_health):
    """绑定之后、Agent 就绪之前，别的 worker 只能看到「忙」，读路径只能看到「没有 Runtime」。"""
    project_id, conversation_id = ids()
    agent_health.healthy = False
    starting = asyncio.create_task(provider.ensure(project_id=project_id, conversation_id=conversation_id))
    try:
        await wait_until_probing(agent_health)

        with pytest.raises(AgentWorkspaceBusyError, match="still starting its Agent"):
            await other_worker.ensure(project_id=project_id, conversation_id=conversation_id)
        with pytest.raises(AgentWorkspaceBusyError):
            await other_worker.ensure(project_id=project_id, conversation_id=str(uuid4()))
        assert await other_worker.peek(conversation_id) is None
        assert await other_worker.preview_target(conversation_id) is None
    finally:
        agent_health.healthy = True
        handle = await starting

    # Once the Agent answered, the same sandbox is served to everyone, and nothing was killed.
    assert await other_worker.ensure(project_id=project_id, conversation_id=conversation_id) == handle
    assert e2b.create_calls == 1
    assert not e2b.sandboxes["sbx-1"].killed


async def test_a_start_left_behind_by_a_dead_worker_is_reclaimed(e2b, provider, other_worker):
    """启动 Agent 的 worker 死在半路，留下「已绑定、未启动」的记录。宽限期过后，沙箱要被杀掉并换一个。"""
    project_id, conversation_id = ids()
    await provider.ensure(project_id=project_id, conversation_id=conversation_id)
    grace = CONFIG.startup_timeout_seconds + e2b_module.STARTUP_GRACE_MARGIN_SECONDS
    await E2BSandboxRecord.objects.filter(conversation_id=conversation_id).aupdate(
        agent_pid=None, updated_at=timezone.now() - timedelta(seconds=grace + 1)
    )

    replacement = await other_worker.ensure(project_id=project_id, conversation_id=conversation_id)

    assert e2b.sandboxes["sbx-1"].killed
    assert replacement.base_url.endswith("sbx-2.sandbox.example")
    stale = await E2BSandboxRecord.objects.aget(sandbox_id="sbx-1")
    assert (stale.active_conversation_id, stale.stop_reason) == (None, "abandoned")


async def test_a_start_cancelled_midway_gives_its_sandbox_back(e2b, provider, agent_health):
    """请求在等 Agent 就绪时被断开：沙箱、占位、事件流都要收拾干净。"""
    project_id, conversation_id = ids()
    agent_health.healthy = False
    task = asyncio.create_task(provider.ensure(project_id=project_id, conversation_id=conversation_id))
    await wait_until_probing(agent_health)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert e2b.sandboxes["sbx-1"].killed
    assert e2b.sandboxes["sbx-1"].commands.processes[0].disconnected
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.agent_pid, record.stop_reason) == (None, None, "failed")


async def test_terminating_a_sandbox_still_starting_its_agent_stops_it(e2b, provider, other_worker, agent_health):
    """启动中也能结束会话；正在启动的那个请求随后发现占位已被释放，不会把 Agent 记成已启动。"""
    project_id, conversation_id = ids()
    agent_health.healthy = False
    starting = asyncio.create_task(provider.ensure(project_id=project_id, conversation_id=conversation_id))
    await wait_until_probing(agent_health)

    await other_worker.terminate(conversation_id)
    agent_health.healthy = True

    with pytest.raises(AgentProvisionError, match="released while its Agent was starting"):
        await starting
    assert e2b.sandboxes["sbx-1"].killed
    record = await E2BSandboxRecord.objects.aget(conversation_id=conversation_id)
    assert (record.active_conversation_id, record.agent_pid, record.stop_reason) == (None, None, "terminated")
