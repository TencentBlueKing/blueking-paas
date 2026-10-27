"""The run slot, and the task that drives a run once it has been admitted.

The supervisor is tested on its own here, with plain async iterators standing in for the AG-UI
stream: what it owes the rest of the Runtime -- the slot handed back exactly once, wind-down
before the stream closes, a broken stream still ending in an event -- does not depend on there
being a model behind it.
"""

import asyncio
from collections.abc import AsyncIterator

from app_spark_agent.server.run_task import RunEvents, RunStopper, RunSupervisor
from app_spark_agent.server.runtime import RunGuard


async def test_a_lease_holds_the_slot_until_released() -> None:
    guard = RunGuard()
    first = await guard.try_acquire()
    assert first is not None
    assert guard.busy is True
    assert await guard.try_acquire() is None

    first.release()
    assert guard.busy is False


async def test_releasing_a_lease_twice_does_not_release_the_next_run() -> None:
    guard = RunGuard()
    first = await guard.try_acquire()
    assert first is not None
    first.release()

    second = await guard.try_acquire()
    assert second is not None
    first.release()
    assert guard.busy is True
    second.release()
    assert guard.busy is False


async def collect(chunks: AsyncIterator[str]) -> list[str]:
    return [chunk async for chunk in chunks]


async def test_a_late_subscriber_still_reads_the_run_from_its_first_event() -> None:
    events = RunEvents()
    events.append("a")
    events.append("b")
    following = asyncio.create_task(collect(events.subscribe()))
    await asyncio.sleep(0)

    events.append("c")
    events.close()

    assert await following == ["a", "b", "c"]
    # A subscriber arriving after the end gets the whole run too, and is not left waiting.
    assert await collect(events.subscribe()) == ["a", "b", "c"]


class Recorder:
    """What the supervisor called back with, in the order it did."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def finish(self, completed: bool) -> None:
        self.calls.append(f"finish:{completed}")

    def release(self) -> None:
        self.calls.append("release")


async def chunks_of(*items: str) -> AsyncIterator[str]:
    for item in items:
        yield item


async def test_the_run_winds_down_before_its_stream_ends() -> None:
    supervisor = RunSupervisor()
    seen = Recorder()

    run = supervisor.start(
        run_id="r1",
        stopper=RunStopper(),
        events=chunks_of("a", "b"),
        finish=seen.finish,
        release=seen.release,
        error_frame=lambda message: f"error:{message}",
    )
    assert supervisor.current is run

    assert await collect(run.events.subscribe()) == ["a", "b"]
    # Reaching the end of the stream already implies the slot is free: that ordering is what a
    # client relies on when it reads /health right after the stream closes.
    assert seen.calls == ["finish:True", "release"]
    assert supervisor.current is None


async def test_a_broken_stream_ends_in_an_error_event_and_still_frees_the_slot() -> None:
    async def breaking() -> AsyncIterator[str]:
        yield "a"
        raise RuntimeError("disk full")

    supervisor = RunSupervisor()
    seen = Recorder()
    run = supervisor.start(
        run_id="r1",
        stopper=RunStopper(),
        events=breaking(),
        finish=seen.finish,
        release=seen.release,
        error_frame=lambda message: f"error:{message}",
    )

    received = await collect(run.events.subscribe())
    assert received[0] == "a"
    assert received[1].startswith("error:")
    assert "disk full" in received[1]
    assert seen.calls == ["finish:False", "release"]


async def test_a_wind_down_that_fails_still_frees_the_slot() -> None:
    supervisor = RunSupervisor()
    released: list[bool] = []

    async def failing_finish(completed: bool) -> None:
        raise RuntimeError("commit failed")

    run = supervisor.start(
        run_id="r1",
        stopper=RunStopper(),
        events=chunks_of("a"),
        finish=failing_finish,
        release=lambda: released.append(True),
        error_frame=lambda message: message,
    )

    assert await collect(run.events.subscribe()) == ["a"]
    assert released == [True]


async def test_a_stop_names_the_run_it_means() -> None:
    gate = asyncio.Event()

    async def held() -> AsyncIterator[str]:
        await gate.wait()
        yield "a"

    supervisor = RunSupervisor()
    seen = Recorder()
    run = supervisor.start(
        run_id="r1",
        stopper=RunStopper(),
        events=held(),
        finish=seen.finish,
        release=seen.release,
        error_frame=lambda message: message,
    )

    assert supervisor.request_stop("another") is False
    assert run.stopper.requested is False
    assert supervisor.request_stop("r1") is True
    assert supervisor.request_stop("r1") is True
    assert run.stopper.requested is True

    gate.set()
    await run.task
    # Once it is over there is nothing left to stop.
    assert supervisor.request_stop("r1") is False


async def test_shutdown_cancels_a_run_that_does_not_stop_in_time() -> None:
    async def stuck() -> AsyncIterator[str]:
        yield "a"
        # A stop request reaches pydantic-ai through the run context, which this stand-in does
        # not have, so nothing but cancelling the task ends it.
        await asyncio.Event().wait()
        yield "never"

    supervisor = RunSupervisor()
    seen = Recorder()
    run = supervisor.start(
        run_id="r1",
        stopper=RunStopper(),
        events=stuck(),
        finish=seen.finish,
        release=seen.release,
        error_frame=lambda message: message,
    )
    await asyncio.sleep(0.01)

    await supervisor.aclose(timeout_seconds=0.05)

    assert run.task.done()
    assert supervisor.closing is True
    assert supervisor.current is None
    # Cancelled outright, it still winds down: the files get their commit, as an interrupted turn.
    assert seen.calls == ["finish:False", "release"]
    assert await collect(run.events.subscribe()) == ["a"]


async def test_shutdown_with_no_run_in_progress_returns_at_once() -> None:
    supervisor = RunSupervisor()
    await supervisor.aclose(timeout_seconds=0)
    assert supervisor.closing is True
