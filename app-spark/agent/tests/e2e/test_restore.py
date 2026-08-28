"""Moving a conversation: across a restart of the same process, then into a cold Runtime.

A Runtime is disposable, the conversation is not. Two different transfers have to work, and
they are not the same transfer: a restart finds its own state directory intact and reloads
everything, while a cold Runtime is handed a context document over HTTP and has to resume from
that alone -- no transcript, no UI events, only the trusted history.

Both are driven here in one chain, because the second only means anything if the first produced
a conversation worth moving.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import console
from tests.e2e.conftest import StartRuntime

pytestmark = pytest.mark.live

HEADING = "<h1>Hello World</h1>"
CREATE = f"Create only index.html containing exactly {HEADING}. Reply DONE."
RECALL_HEADING = "Without using tools, reply only with the page heading text."

# A version no Runtime under test could have reached, so `If-Match` has to reject it.
IMPOSSIBLE_VERSION = "99"


def test_a_conversation_survives_a_restart_and_moves_to_a_cold_runtime(
    start_runtime: StartRuntime,
    workspace: Path,
    conversation_id: str,
) -> None:
    console.banner("phase 1: a conversation worth moving")
    hot = start_runtime(state="hot")
    first = hot.turn(conversation_id=conversation_id, prompt=CREATE)
    assert "DONE" in first.reply.upper()
    assert (workspace / "index.html").read_text().strip() == HEADING

    health = hot.health()
    exported = hot.context()
    assert exported["conversation_id"] == conversation_id
    hot.stop()

    console.banner("phase 2: a new process opens the same state directory")
    restarted = start_runtime(state="hot")
    reopened = restarted.health()
    # Nothing was hydrated from anywhere: the state directory is the whole recovery path.
    assert restarted.context() == exported
    assert reopened["conversation_id"] == conversation_id
    assert reopened["log_seq"] == health["log_seq"]
    assert reopened["ui_event_seq"] == health["ui_event_seq"]
    restarted.stop()

    console.banner("phase 3: an empty Runtime is handed the context over HTTP")
    cold = start_runtime(state="cold")
    stale = cold.restore(exported, if_match=IMPOSSIBLE_VERSION)
    assert stale.status_code == 412, stale.text

    restored = cold.restore(exported, if_match="0")
    assert restored.status_code == 200, restored.text
    assert restored.headers["etag"] == str(exported["context_version"])

    console.banner("phase 4: the conversation continues where it left off")
    resumed = cold.turn(conversation_id=conversation_id, prompt=RECALL_HEADING)
    assert "hello world" in resumed.reply.lower()

    resumed_health = cold.health()
    assert resumed_health["context_version"] > exported["context_version"]
    # A cold Runtime starts its own logs: what moved was the context, not the history.
    assert 0 < resumed_health["log_seq"] < health["log_seq"]
