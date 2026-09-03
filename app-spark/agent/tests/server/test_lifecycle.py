"""Idle clock and app-child registry: fake clock plus real subprocesses."""

from __future__ import annotations

import subprocess
import sys

import pytest

from app_spark_agent.server.lifecycle import AppProcessRegistry, IdleWatch, RuntimeLifecycle
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


def test_idle_timeout_stops_children_then_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    AppProcessRegistry().stop_all()

    exits: list[int] = []
    monkeypatch.setattr("app_spark_agent.server.lifecycle.os._exit", exits.append)
    clock = FakeClock()
    life = RuntimeLifecycle.create(timeout_seconds=10, clock=clock)
    child = _sleeping_child()
    life.processes.register(child)
    try:
        clock.advance(10)
        assert life.idle.fire_if_due() is True
        assert child.poll() is not None
        assert exits == [0]
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
