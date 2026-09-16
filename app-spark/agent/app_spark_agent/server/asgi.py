"""ASGI entry point for an external server.

The production entry is `python -m app_spark_agent`, which sets
`timeout_graceful_shutdown`. If you run `uvicorn app_spark_agent.server.asgi:app`
directly, pass `--timeout-graceful-shutdown` as well, or SIGTERM waits forever
for in-flight SSE.

configure_logging is idempotent and must run here too: this module is what
e2e and any external ASGI server import, and they never go through __main__.
"""

from app_spark_agent.observability import configure_logging
from app_spark_agent.server.app import create_app_from_settings

configure_logging()
app = create_app_from_settings()
