"""ASGI entry point for an external server.

The production entry is `python -m app_spark_agent`, which sets
`timeout_graceful_shutdown`. If you run `uvicorn app_spark_agent.server.asgi:app`
directly, pass `--timeout-graceful-shutdown` as well, or SIGTERM waits forever
for in-flight SSE.
"""

from app_spark_agent.server.app import create_app_from_settings

app = create_app_from_settings()
