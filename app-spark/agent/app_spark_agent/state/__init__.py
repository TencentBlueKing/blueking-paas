"""Durable state for one Agent conversation, split by how each stream mutates.

Two shapes, three streams:

- :mod:`app_spark_agent.state.log` -- append-only channels. The raw model transcript and the
  AG-UI event history are both write-once logs ordered by a monotonic sequence number.
- :mod:`app_spark_agent.state.context` -- the single mutable blob holding the history that is
  actually sent to the model. Compaction rewrites it, so it is replaced atomically and carries
  its own version.
"""

from app_spark_agent.state.context import (
    STATE_SCHEMA_VERSION,
    ContextStore,
    ConversationContext,
    ConversationStateConflict,
    ConversationStateError,
)
from app_spark_agent.state.log import AppendLog, AppendLogError, LogRecord

__all__ = [
    "STATE_SCHEMA_VERSION",
    "AppendLog",
    "AppendLogError",
    "ContextStore",
    "ConversationContext",
    "ConversationStateConflict",
    "ConversationStateError",
    "LogRecord",
]
