"""Bind the Agent HTTP server to 0.0.0.0."""

import os
from urllib.parse import urlsplit

import uvicorn

from app_spark_agent import settings
from app_spark_agent.observability import AGENT_LOG_PATH, configure_logging, log
from app_spark_agent.server.app import create_app_from_settings


def _git_remote_for_log() -> str:
    """Return the remote host and path, never the userinfo.

    The clone URL is injected by the control plane and is not supposed to carry the token, but
    a URL that does would otherwise land in the sandbox log in clear text.
    """
    if not settings.is_git_configured():
        return "off"
    parts = urlsplit(settings.GIT_REMOTE_URL)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return f"{parts.scheme}://{host}{parts.path}"


def main() -> None:
    """Start uvicorn on ``0.0.0.0:<APP_SPARK_AGENT_PORT>``."""
    configure_logging()
    # First line of a live process. Its absence in /data/agent.log means this process never got
    # this far; the file is not created by the sandbox entrypoint.
    log.info(
        "agent process started pid=%s listen=0.0.0.0:%s app_port=%s workspace=%s git_remote=%s log_file=%s",
        os.getpid(),
        settings.PORT,
        settings.APP_PORT,
        settings.WORKSPACE or settings.DEFAULT_WORKSPACE,
        _git_remote_for_log(),
        AGENT_LOG_PATH,
    )
    # Default drain wait is unbounded; an in-flight SSE would hold SIGTERM until the
    # run ends and might persist that turn as success. A short timeout drops the
    # connection, then lifespan drains and calls stop_all. A cancelled run skips
    # on_complete. This bounds waiting for *connections* only -- uvicorn gives the
    # lifespan shutdown itself no deadline, which is why the drain brings its own.
    uvicorn.run(
        create_app_from_settings(),
        host="0.0.0.0",
        port=settings.PORT,
        timeout_graceful_shutdown=settings.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
        # Uvicorn would otherwise install its own handlers on the loggers
        # `configure_logging` just pointed at the root, restoring unmasked output.
        log_config=None,
    )


if __name__ == "__main__":
    main()
