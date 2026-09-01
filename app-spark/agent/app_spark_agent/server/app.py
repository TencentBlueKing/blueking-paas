"""Assembly of the Runtime application from its runtime state and its views."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic_ai import Agent

from app_spark_agent import VERSION, settings
from app_spark_agent.replication import ControlPlaneClient
from app_spark_agent.server.errors import install_error_handlers
from app_spark_agent.server.lifecycle import RuntimeLifecycle
from app_spark_agent.server.routes import attach_runtime, router
from app_spark_agent.server.runtime import ConversationRuntime


def create_runtime_app(
    *,
    workspace: Path,
    state_dir: Path,
    agent: Agent[Any, Any] | None = None,
    lifecycle: RuntimeLifecycle | None = None,
    control_plane: ControlPlaneClient | None = None,
) -> FastAPI:
    """Create one conversation-exclusive Agent Runtime application.

    Three streams are persisted under ``state_dir``, split by how each one mutates: an
    append-only raw transcript, an append-only AG-UI event history, and the single mutable
    context blob compaction rewrites. See ``README.md`` for why the context can never be
    rebuilt from the transcript.

    When a control plane is supplied all three are also replicated to it, which is what makes
    ``state_dir`` disposable. Without one the Runtime is entirely self-contained.

    :param workspace: Existing directory exposed to coding tools.
    :param state_dir: Directory outside ``workspace`` holding the conversation's durable state.
    :param agent: Optional preconfigured agent, primarily for embedding the Runtime or for tests.
    :param lifecycle: Optional idle / SIGTERM controller; created from settings when omitted.
    :param control_plane: Optional client the durable state is replicated to.
    :return: A FastAPI application exposing health, drain, context, and AG-UI run endpoints.
    """
    runtime = ConversationRuntime.open(
        workspace=workspace,
        state_dir=state_dir,
        agent=agent,
        lifecycle=lifecycle,
        control_plane=control_plane,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Run lifecycle monitoring and replication while the server is serving.

        The replicator starts here rather than in :meth:`ConversationRuntime.open`, because it
        owns a task and a connection pool, and neither may outlive the event loop the server
        creates.
        """
        if runtime.replicator is not None:
            await runtime.replicator.start()
        lifecycle_task = asyncio.create_task(runtime.lifecycle.watch())
        try:
            yield
        finally:
            lifecycle_task.cancel()
            try:
                with suppress(asyncio.CancelledError):
                    await lifecycle_task
                if runtime.replicator is not None:
                    try:
                        # A last attempt to hand over whatever the background task had not
                        # reached, so an orderly shutdown does not strand a completed turn.
                        await runtime.flush_replication()
                    finally:
                        await runtime.replicator.aclose()
            finally:
                await asyncio.to_thread(runtime.lifecycle.shutdown)

    app = FastAPI(title="App-Spark Agent Runtime", version=VERSION, lifespan=lifespan)
    # The views read the runtime back through a dependency, which is what keeps them plain
    # module-level functions instead of closures over this factory.
    attach_runtime(app, runtime)
    install_error_handlers(app)
    app.include_router(router)
    return app


def create_app_from_settings() -> FastAPI:
    """Create the application described entirely by the environment.

    When `APP_SPARK_AGENT_WORKSPACE` / `APP_SPARK_AGENT_STATE_DIR` are unset, fall
    back to `/data/workspace` and `/data/state`.

    :return: A FastAPI application for the configured workspace and state directory.
    """
    workspace = settings.WORKSPACE or Path(settings.DEFAULT_WORKSPACE)
    state_dir = settings.STATE_DIR or Path(settings.DEFAULT_STATE_DIR)
    return create_runtime_app(
        workspace=workspace,
        state_dir=state_dir,
        control_plane=_control_plane_from_settings(),
    )


def _control_plane_from_settings() -> ControlPlaneClient | None:
    """Build the control plane client the environment describes, if it describes one.

    An unset URL is not an error: it is how a Runtime is told that it is on its own, which is
    the shape used for local development and for the whole test suite.
    """
    if not settings.CONTROL_PLANE_URL:
        return None
    # Guaranteed present alongside the URL; `settings` refuses to import with only one of them.
    assert settings.CONTROL_PLANE_TOKEN is not None
    return ControlPlaneClient(
        base_url=settings.CONTROL_PLANE_URL,
        token=settings.CONTROL_PLANE_TOKEN,
        timeout_seconds=settings.CONTROL_PLANE_TIMEOUT_SECONDS,
    )
