"""Assembly of the Runtime application from its runtime state and its views."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic_ai import Agent

from app_spark_agent import VERSION, settings
from app_spark_agent.server.lifecycle import RuntimeLifecycle
from app_spark_agent.server.routes import attach_runtime, busy_conflict_handler, router
from app_spark_agent.server.runtime import ConversationRuntime, RuntimeBusyError


def create_runtime_app(
    *,
    workspace: Path,
    state_dir: Path,
    agent: Agent[Any, Any] | None = None,
    lifecycle: RuntimeLifecycle | None = None,
) -> FastAPI:
    """Create one conversation-exclusive Agent Runtime application.

    Three streams are persisted under ``state_dir``, split by how each one mutates: an
    append-only raw transcript, an append-only AG-UI event history, and the single mutable
    context blob compaction rewrites. See ``README.md`` for why the context can never be
    rebuilt from the transcript.

    :param workspace: Existing directory exposed to coding tools.
    :param state_dir: Directory outside ``workspace`` holding the conversation's durable state.
    :param agent: Optional preconfigured agent, primarily for embedding the Runtime or for tests.
    :param lifecycle: Optional idle / SIGTERM controller; created from settings when omitted.
    :return: A FastAPI application exposing health, drain, context, and AG-UI run endpoints.
    """
    runtime = ConversationRuntime.open(
        workspace=workspace,
        state_dir=state_dir,
        agent=agent,
        lifecycle=lifecycle,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(runtime.lifecycle.watch())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(runtime.lifecycle.shutdown)

    app = FastAPI(title="App-Spark Agent Runtime", version=VERSION, lifespan=lifespan)
    # The views read the runtime back through a dependency, which is what keeps them plain
    # module-level functions instead of closures over this factory.
    attach_runtime(app, runtime)
    app.add_exception_handler(RuntimeBusyError, busy_conflict_handler)
    app.include_router(router)
    return app


def create_app_from_settings() -> FastAPI:
    """Create the application described entirely by the environment.

    When `APP_SPARK_AGENT_WORKSPACE` / `APP_SPARK_AGENT_STATE_DIR` are unset, fall
    back to `/workspace` and `/state`.

    :return: A FastAPI application for the configured workspace and state directory.
    """
    workspace = settings.WORKSPACE or Path(settings.DEFAULT_WORKSPACE)
    state_dir = settings.STATE_DIR or Path(settings.DEFAULT_STATE_DIR)
    return create_runtime_app(workspace=workspace, state_dir=state_dir)
