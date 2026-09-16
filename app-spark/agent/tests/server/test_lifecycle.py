"""Idle clock and app-child registry: fake clock plus real subprocesses."""

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable

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
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


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
