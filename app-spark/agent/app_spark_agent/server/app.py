"""Assembly of the Runtime application from its runtime state and its views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from environs import EnvError
from fastapi import FastAPI
from pydantic_ai import Agent

from app_spark_agent import settings
from app_spark_agent.server.routes import attach_runtime, busy_conflict_handler, router
from app_spark_agent.server.runtime import ConversationRuntime, RuntimeBusyError


def create_runtime_app(
    *,
    workspace: Path,
    state_dir: Path,
    agent: Agent[Any, Any] | None = None,
) -> FastAPI:
    """Create one conversation-exclusive Agent Runtime application.

    Three streams are persisted under ``state_dir``, split by how each one mutates: an
    append-only raw transcript, an append-only AG-UI event history, and the single mutable
    context blob compaction rewrites. See ``README.md`` for why the context can never be
    rebuilt from the transcript.

    :param workspace: Existing directory exposed to coding tools.
    :param state_dir: Directory outside ``workspace`` holding the conversation's durable state.
    :param agent: Optional preconfigured agent, primarily for embedding the Runtime or for tests.
    :return: A FastAPI application exposing health, drain, context, and AG-UI run endpoints.
    """
    runtime = ConversationRuntime.open(workspace=workspace, state_dir=state_dir, agent=agent)

    app = FastAPI(title="App-Spark Agent Runtime")
    # The views read the runtime back through a dependency, which is what keeps them plain
    # module-level functions instead of closures over this factory.
    attach_runtime(app, runtime)
    app.add_exception_handler(RuntimeBusyError, busy_conflict_handler)
    app.include_router(router)
    return app


def create_app_from_settings() -> FastAPI:
    """Create the application described entirely by the environment.

    This is the entry point an external ASGI server reaches the Runtime through, so the two
    directories that have no sensible default are required here rather than at import time --
    importing the settings must stay possible without them.

    :return: A FastAPI application for the configured workspace and state directory.
    :raises environs.EnvError: If the workspace or state directory is not configured.
    """
    missing = [
        f"{settings.ENV_PREFIX}{name}"
        for name, value in (("WORKSPACE", settings.WORKSPACE), ("STATE_DIR", settings.STATE_DIR))
        if value is None
    ]
    if missing:
        raise EnvError(f"Required environment variable(s) not set: {', '.join(missing)}")

    # Narrowed by the check above; the settings themselves are deliberately optional.
    assert settings.WORKSPACE is not None
    assert settings.STATE_DIR is not None
    return create_runtime_app(workspace=settings.WORKSPACE, state_dir=settings.STATE_DIR)
