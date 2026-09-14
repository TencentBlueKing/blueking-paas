"""Process lifecycle: idle-timeout exit, and stop registered app children on SIGTERM."""

import asyncio
import logging
import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from app_spark_agent import settings

logger = logging.getLogger(__name__)


class IdleWatch:
    """Exit after idle time measured from process start, reset when ``POST /runs`` ends.

    Construction starts the clock: a Runtime that never receives a run still exits
    when the timeout elapses. ``/health`` and other probes must not call :meth:`mark_idle`.
    ``timeout_seconds <= 0`` makes the watch a no-op: the process never exits for idle.

    :param timeout_seconds: Idle seconds; ``<= 0`` disables exit.
    :param is_busy: Whether a run is still open; when true, timeout does not exit.
    :param clock: Monotonic clock; tests may inject one.
    :param on_timeout: Fired when due; defaults to ``os._exit(0)``. Production replaces
        this in :meth:`RuntimeLifecycle.create` with an orderly shutdown request.
    :param poll_interval: Sleep between watch-loop checks.
    """

    def __init__(
        self,
        timeout_seconds: float,
        *,
        is_busy: Callable[[], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
        on_timeout: Callable[[], None] | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.is_busy = is_busy or (lambda: False)
        self._clock = clock
        # A standalone IdleWatch exits immediately; create() wraps this with stop_all then _exit.
        self._on_timeout = on_timeout or (lambda: os._exit(0))
        self._poll_interval = poll_interval
        # Process start is the first idle origin; mark_idle() moves it after each run.
        self.last_idle_origin = clock()

    def mark_idle(self) -> None:
        """Reset the idle origin to now. Call only when ``POST /runs`` ends."""
        self.last_idle_origin = self._clock()

    def due(self) -> bool:
        """Return whether idle timeout should fire now."""
        if self.timeout_seconds <= 0:
            return False
        if self.is_busy():
            return False
        return self._clock() - self.last_idle_origin >= self.timeout_seconds

    def fire_if_due(self) -> bool:
        """Call ``on_timeout`` and return ``True`` when due."""
        if not self.due():
            return False
        self._on_timeout()
        return True

    async def watch(self) -> None:
        """Poll until due or the task is cancelled.

        ``timeout_seconds <= 0`` returns immediately and starts no loop.
        """
        if self.timeout_seconds <= 0:
            return
        while True:
            if self.fire_if_due():
                return
            await asyncio.sleep(self._poll_interval)


class AppProcessRegistry:
    """Track application children started by the Agent so SIGTERM can stop them.

    Empty until the app manager lands: :meth:`stop_all` is then a no-op
    ("no apps means zero children").
    """

    def __init__(self) -> None:
        self._processes: list[subprocess.Popen[bytes]] = []

    def register(self, process: subprocess.Popen[bytes]) -> None:
        """Register a child this process started."""
        self._processes.append(process)

    def living(self) -> list[subprocess.Popen[bytes]]:
        """Registered processes that have not exited."""
        return [process for process in self._processes if process.poll() is None]

    def stop_all(self, timeout: float = 5.0) -> None:
        """SIGTERM first, then SIGKILL whoever is still alive. Empty registry is fine."""
        living = self.living()
        if not living:
            self._processes.clear()
            return

        deadline = time.monotonic() + timeout
        for process in living:
            process.terminate()
        for process in living:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    pass
        self._processes.clear()


class RuntimeLifecycle:
    """Idle clock and application-child registry for one Runtime process."""

    def __init__(self, idle: IdleWatch, processes: AppProcessRegistry) -> None:
        self.idle = idle
        self.processes = processes

    @classmethod
    def create(
        cls,
        *,
        timeout_seconds: float | None = None,
        is_busy: Callable[[], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
        on_timeout: Callable[[], None] | None = None,
        poll_interval: float = 1.0,
    ) -> RuntimeLifecycle:
        """Build a lifecycle from settings.

        :param timeout_seconds: Override ``APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS``; ``None`` uses settings.
        """
        seconds = settings.IDLE_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        processes = AppProcessRegistry()

        def hard_exit() -> None:
            """Leave now, having stopped the children nothing else will reap."""
            try:
                processes.stop_all()
            except Exception:
                # Nothing here may keep the process alive: this is the path that exists because
                # something else already failed to finish.
                logger.exception("could not stop the application children before the hard exit")
            os._exit(0)

        def request_orderly_shutdown() -> None:
            """Ask the server to stop the way a SIGTERM does, and leave anyway if it will not.

            Signalling rather than exiting outright is the whole point. ``os._exit`` skips the
            lifespan shutdown, and the lifespan shutdown is where an unpushed workspace commit
            and un-replicated state get their last chance to leave the sandbox -- so idling out
            used to discard exactly the work this timeout exists to stop paying for. Going
            through the server's own path also means teardown added later is teardown this path
            inherits, instead of the next thing it quietly skips.

            The watchdog keeps the guarantee the old ``os._exit`` provided: however wedged the
            shutdown gets, an idle Runtime stops costing money.
            """
            _exit_after(settings.IDLE_EXIT_DEADLINE_SECONDS, hard_exit)
            # Delivered to this process, whose uvicorn installed the handler that turns it into
            # a graceful shutdown. tini is PID 1 in the image, so this is never PID 1.
            os.kill(os.getpid(), signal.SIGTERM)

        return cls(
            idle=IdleWatch(
                seconds,
                is_busy=is_busy,
                clock=clock,
                on_timeout=on_timeout or request_orderly_shutdown,
                poll_interval=poll_interval,
            ),
            processes=processes,
        )

    def attach(self, guard: Any) -> None:
        """Wire the idle clock to this Runtime's run slot.

        Busy blocks idle exit; the clock resets only when ``POST /runs`` releases
        its lease. Injected lifecycles go through here so callers need not patch
        ``idle.is_busy`` afterwards. ``guard`` must expose ``busy`` and
        ``notify_run_end`` (that is :class:`RunGuard`).
        """
        self.idle.is_busy = lambda: guard.busy
        guard.notify_run_end(self.idle.mark_idle)

    async def watch(self) -> None:
        """Start idle watching."""
        await self.idle.watch()

    def shutdown(self) -> None:
        """Stop registered application children. Does not commit conversation context."""
        self.processes.stop_all()


def _exit_after(seconds: float, exit_now: Callable[[], None]) -> threading.Thread:
    """Run ``exit_now`` once ``seconds`` have passed, unless the process is gone by then.

    A daemon thread rather than a task, because the event loop is precisely what may be wedged
    -- or have had its tasks cancelled -- by the time this matters. When the orderly shutdown
    wins the race, which is the ordinary outcome, the thread dies with the process and never
    runs. That is why it may not do anything but exit: it cannot tell the two cases apart.

    :param seconds: How long the orderly shutdown gets before it is overruled.
    :param exit_now: What to call when it runs out of time.
    :return: The started thread, so tests can wait for it.
    """

    def wait_then_exit() -> None:
        time.sleep(seconds)
        logger.warning("the orderly shutdown did not finish within %.0fs; exiting the hard way", seconds)
        exit_now()

    thread = threading.Thread(target=wait_then_exit, name="idle-exit-watchdog", daemon=True)
    thread.start()
    return thread
