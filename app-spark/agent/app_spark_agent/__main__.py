"""Bind the Agent HTTP server to 0.0.0.0."""

from __future__ import annotations

import uvicorn

from app_spark_agent import settings
from app_spark_agent.server.app import create_app_from_settings


def main() -> None:
    """Start uvicorn on ``0.0.0.0:<APP_SPARK_AGENT_PORT>``."""
    # Default drain wait is unbounded; an in-flight SSE would hold SIGTERM until the
    # run ends and might persist that turn as success. A short timeout drops the
    # connection, then lifespan calls stop_all. A cancelled run skips on_complete.
    uvicorn.run(
        create_app_from_settings(),
        host="0.0.0.0",
        port=settings.PORT,
        timeout_graceful_shutdown=settings.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
    )


if __name__ == "__main__":
    main()
