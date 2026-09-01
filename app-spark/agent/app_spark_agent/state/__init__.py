"""Durable state for one Agent conversation, split by how each stream mutates.

Two shapes, three streams:

- :mod:`app_spark_agent.state.log` -- append-only channels. The raw model transcript and the
  AG-UI event history are both write-once logs ordered by a monotonic sequence number.
- :mod:`app_spark_agent.state.context` -- the single mutable blob holding the history that is
  actually sent to the model. Compaction rewrites it, so it is replaced atomically and carries
  its own version.

Two supporting pieces exist because the state is replicated to a control plane rather than only
kept locally: :mod:`app_spark_agent.state.cursors` remembers where each channel starts and how
far it has been pushed, and :mod:`app_spark_agent.state.signal` is the flag a commit raises so
the replicator does not have to poll.
"""

from app_spark_agent.state.context import (
    STATE_SCHEMA_VERSION,
    ContextStore,
    ConversationContext,
    ConversationStateConflict,
    ConversationStateError,
)
from app_spark_agent.state.cursors import (
    CURSORS_SCHEMA_VERSION,
    Channel,
    ChannelCursor,
    CursorStateError,
    CursorStore,
)
from app_spark_agent.state.log import AppendLog, AppendLogError, LogPage, LogRecord
from app_spark_agent.state.signal import ChangeSignal

__all__ = [
    "CURSORS_SCHEMA_VERSION",
    "STATE_SCHEMA_VERSION",
    "AppendLog",
    "AppendLogError",
    "ChangeSignal",
    "Channel",
    "ChannelCursor",
    "ContextStore",
    "ConversationContext",
    "ConversationStateConflict",
    "ConversationStateError",
    "CursorStateError",
    "CursorStore",
    "LogPage",
    "LogRecord",
]
