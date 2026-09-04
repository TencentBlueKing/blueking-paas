"""RunLease: releasing a never-started generator must not drop the next run."""

from app_spark_agent.server.runtime import RunGuard


async def test_lease_acquire_busy_and_never_started_release() -> None:
    guard = RunGuard()
    first = await guard.try_acquire()
    assert first is not None
    assert guard.busy is True
    assert await guard.try_acquire() is None

    first.release_if_never_started()
    assert guard.busy is False


async def test_entered_lease_does_not_release_the_next_run() -> None:
    guard = RunGuard()
    first = await guard.try_acquire()
    assert first is not None
    first.mark_entered()
    first.release()

    second = await guard.try_acquire()
    assert second is not None
    first.release_if_never_started()
    assert guard.busy is True
    second.release()
    assert guard.busy is False
