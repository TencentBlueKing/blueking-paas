"""HTTP server for one stateful coding-agent conversation, split by concern.

- :mod:`app_spark_agent.server.runtime` -- the agent, the three durable state channels, and the
  guard that admits one mutating operation at a time. No HTTP.
- :mod:`app_spark_agent.server.run_input` -- the trust boundary: validates an inbound AG-UI run
  and reduces it to a single new user turn.
- :mod:`app_spark_agent.server.routes` -- the views: health, drain, context, launch, and AG-UI run.
- :mod:`app_spark_agent.server.errors` -- exception handlers: 409 mapping and credential
  masking on HTTP error bodies.
- :mod:`app_spark_agent.server.lifecycle` -- idle timeout and SIGTERM child-process registry.
- :mod:`app_spark_agent.server.app` -- assembles the two halves into a FastAPI application.
- :mod:`app_spark_agent.server.asgi` -- the module an external ASGI server is pointed at.
"""

from app_spark_agent.server.app import create_app_from_settings, create_runtime_app
from app_spark_agent.server.runtime import (
    CONTEXT_FILENAME,
    TRANSCRIPT_FILENAME,
    UI_EVENTS_FILENAME,
    ConversationRuntime,
    RunGuard,
    RunLease,
    RuntimeBusyError,
)

__all__ = [
    "CONTEXT_FILENAME",
    "TRANSCRIPT_FILENAME",
    "UI_EVENTS_FILENAME",
    "ConversationRuntime",
    "RunGuard",
    "RunLease",
    "RuntimeBusyError",
    "create_app_from_settings",
    "create_runtime_app",
]
