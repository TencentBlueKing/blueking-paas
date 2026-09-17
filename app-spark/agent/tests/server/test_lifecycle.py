"""Idle clock and app-child registry: fake clock plus real subprocesses."""

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from app_spark_agent import settings
from app_spark_agent.server import lifecycle
from app_spark_agent.server.lifecycle import (
    AppProcessRegistry,
    IdleWatch,
    RuntimeLifecycle,
    _exit_after,
)
from app_spark_agent.server.runtime import RunGuard


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _sleeping_child() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )


# 组内的第二个进程，没有被登记过：它只有在信号打到整个进程组时才会收到 SIGTERM。
# 收到就写标记文件，测试据此判断，而不是去看它的 pid 还在不在——孤儿进程会被 reparent 到
# PID 1，容器里的 PID 1 不一定回收子进程，僵尸状态下 os.kill(pid, 0) 照样成功。
_GROUP_MEMBER = """
import os
import signal
import sys
import time

marker, ready = sys.argv[1], sys.argv[2]


def on_term(signum, frame):
    with open(marker, "w") as handle:
        handle.write("term")
    os._exit(0)


signal.signal(signal.SIGTERM, on_term)
with open(ready, "w") as handle:
    handle.write("up")
time.sleep(60)
"""

# 被登记的那个进程：自己不做事，只负责在同一个进程组里再拉起一个。
_GROUP_LEADER = """
import subprocess
import sys
import time

member, marker, ready = sys.argv[1], sys.argv[2], sys.argv[3]
subprocess.Popen([sys.executable, "-c", member, marker, ready])
time.sleep(60)
"""


def _wait_for(path: Path, *, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.02)
    return False


def test_idle_watch_timeout_busy_and_reset() -> None:
    clock = FakeClock()
    fired: list[int] = []
    watch = IdleWatch(10, clock=clock, on_timeout=lambda: fired.append(1))

    clock.advance(9)
    assert watch.fire_if_due() is False
    clock.advance(1)
    assert watch.fire_if_due() is True
    assert fired == [1]

    clock = FakeClock()
    fired.clear()
    watch = IdleWatch(10, clock=clock, on_timeout=lambda: fired.append(1))
    clock.advance(8)
    watch.mark_idle()
    clock.advance(9)
    assert watch.fire_if_due() is False
    clock.advance(1)
    assert watch.fire_if_due() is True

    clock = FakeClock()
    fired.clear()
    busy = True
    watch = IdleWatch(10, is_busy=lambda: busy, clock=clock, on_timeout=lambda: fired.append(1))
    clock.advance(30)
    assert watch.fire_if_due() is False
    busy = False
    assert watch.fire_if_due() is True

    assert IdleWatch(0, clock=FakeClock(), on_timeout=lambda: fired.append(1)).fire_if_due() is False


async def test_attach_blocks_idle_while_a_run_is_held() -> None:
    clock = FakeClock()
    life = RuntimeLifecycle.create(timeout_seconds=10, clock=clock)
    guard = RunGuard()
    life.attach(guard)

    lease = await guard.try_acquire()
    assert lease is not None
    clock.advance(30)
    assert life.idle.due() is False
    lease.release()
    clock.advance(10)
    assert life.idle.due() is True


class TestIdleExit:
    """How an idle Runtime leaves, which decides whether its unsaved work leaves with it."""

    def test_it_asks_the_server_to_stop_rather_than_exiting_on_the_spot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regression: exiting here skipped the shutdown that pushes the workspace.

        The idle path used to call ``os._exit`` itself, so a Runtime that simply went quiet with
        a committed-but-unpushed turn threw that turn away along with the sandbox disk. Going
        through a signal means it runs the same teardown a SIGTERM does.
        """
        signals: list[tuple[int, int]] = []
        exits: list[int] = []
        deadlines: list[float] = []
        monkeypatch.setattr(lifecycle.os, "kill", lambda pid, sig: signals.append((pid, sig)))
        monkeypatch.setattr(lifecycle.os, "_exit", exits.append)
        monkeypatch.setattr(lifecycle, "_exit_after", lambda seconds, exit_now: deadlines.append(seconds))
        clock = FakeClock()
        life = RuntimeLifecycle.create(timeout_seconds=10, clock=clock)

        clock.advance(10)

        assert life.idle.fire_if_due() is True
        assert signals == [(os.getpid(), signal.SIGTERM)]
        assert exits == []
        assert deadlines == [settings.IDLE_EXIT_DEADLINE_SECONDS]

    def test_the_watchdog_stops_the_children_and_exits_when_the_shutdown_does_not(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The safety net: however wedged the shutdown gets, an idle Runtime stops costing money.

        The children are stopped through the registry rather than asserted on a live process
        here: that stop is :meth:`AppProcessRegistry.stop_all`'s job (covered below), and this
        test only needs to know the hard exit still calls it before leaving.
        """
        exits: list[int] = []
        stopped: list[str] = []
        overrule: list[Callable[[], None]] = []
        monkeypatch.setattr(lifecycle.os, "kill", lambda pid, sig: None)
        monkeypatch.setattr(lifecycle.os, "_exit", exits.append)
        monkeypatch.setattr(lifecycle, "_exit_after", lambda seconds, exit_now: overrule.append(exit_now))
        clock = FakeClock()
        life = RuntimeLifecycle.create(timeout_seconds=10, clock=clock)
        monkeypatch.setattr(life.processes, "stop_all", lambda: stopped.append("yes"))

        clock.advance(10)
        assert life.idle.fire_if_due() is True

        # The orderly shutdown running out of its deadline.
        overrule[0]()

        assert stopped == ["yes"]
        assert exits == [0]


def test_the_watchdog_runs_once_its_time_is_up() -> None:
    """Tested through the module function because the closure it guards has no other seam."""
    fired = threading.Event()

    thread = _exit_after(0.01, fired.set)

    assert fired.wait(timeout=5.0) is True
    thread.join(timeout=5.0)


def test_stop_all_terminates_registered_children() -> None:
    """The registry the hard exit leans on actually stops what it was given."""
    registry = AppProcessRegistry()
    child = _sleeping_child()
    registry.register(child)
    try:
        registry.stop_all()
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_stop_all_signals_the_whole_process_group(tmp_path: Path) -> None:
    """A uvicorn that spawned its own workers must not leave them behind holding the port."""
    marker = tmp_path / "member-got-sigterm"
    ready = tmp_path / "member-up"
    leader = subprocess.Popen(
        [sys.executable, "-c", _GROUP_LEADER, _GROUP_MEMBER, str(marker), str(ready)],
        start_new_session=True,
    )
    try:
        assert _wait_for(ready), "the second process in the group never started"
        registry = AppProcessRegistry()
        registry.register(leader)

        registry.stop_all()

        assert leader.poll() is not None
        # 只 terminate 被登记的那个进程时，这个标记永远不会出现。
        assert _wait_for(marker), "the unregistered group member was never signalled"
    finally:
        if leader.poll() is None:
            leader.kill()
            leader.wait()
