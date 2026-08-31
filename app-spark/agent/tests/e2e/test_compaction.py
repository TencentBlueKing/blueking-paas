"""The expensive compaction tier against the real model.

``tests/api/test_compaction.py`` pins what compaction does, deterministically, against a scripted
model. What it cannot pin is the round trip: a summary written by DeepSeek has to survive being
persisted, reloaded, and handed back to the *next* request. That is exactly what
``manage_system_prompt='server'`` used to break -- it strips every ``SystemPromptPart`` from the
history, which is where ``SummarizingCompaction`` keeps its summary, so the summary was
discarded on the request after the one that paid for it and the history re-summarized forever.

Only a real model can produce a real summary, so this is the only place that regression shows.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.e2e import console
from tests.e2e.conftest import StartRuntime
from tests.e2e.live import LiveRuntime, model_messages, part_contents

pytestmark = pytest.mark.live

SUMMARY_PREFIX = "Summary of previous conversation:"

# Far below the fixed overhead of the tool schemas alone, so the escalation is entered on every
# request and the tiers decide what actually happens -- the production 480,000 would need a
# conversation too large to drive from a test.
LIVE_TARGET_TOKENS = "1000"
# The summarizing tier returns the history untouched while it is shorter than this, so the
# production 20 would never let a short live conversation reach the expensive tier.
LIVE_KEEP_MESSAGES = "6"

HEADING = "<h1>Hello World</h1>"
CREATE = f"Create only index.html containing exactly {HEADING}. Reply DONE."
RECALL = "Without using tools, reply with only the heading text of the page you created."

# Deliberately trivial: what grows the history past the summarizing tier's floor is the number
# of messages, not the work in them.
FILLER_TURNS = 4


@pytest.fixture
def compacting_runtime(start_runtime: StartRuntime) -> LiveRuntime:
    """A Runtime whose compaction budget is small enough to fire on every request."""
    return start_runtime(
        state="compacting",
        COMPACTION_TARGET_TOKENS=LIVE_TARGET_TOKENS,
        COMPACTION_KEEP_MESSAGES=LIVE_KEEP_MESSAGES,
    )


def summaries(messages: list[dict[str, Any]]) -> list[str]:
    """Return every part that reads like a compaction summary."""
    return [text for text in part_contents(messages) if text.startswith(SUMMARY_PREFIX)]


def test_a_real_summary_enters_the_context_and_stays_there(
    compacting_runtime: LiveRuntime,
    conversation_id: str,
) -> None:
    runtime = compacting_runtime

    console.banner("a conversation long enough to be worth summarizing")
    runtime.turn(conversation_id=conversation_id, prompt=CREATE)
    for index in range(FILLER_TURNS):
        filler = runtime.turn(
            conversation_id=conversation_id,
            prompt=f"Reply with only the number {index}.",
        )
        assert filler.reply, "an empty turn would grow the history without exercising anything"

    summarized = runtime.context()
    assert summaries(summarized["messages"]), "the summarizing tier never ran against the model"

    console.banner("one more request, which is where a mishandled summary would be lost")
    recalled = runtime.turn(conversation_id=conversation_id, prompt=RECALL)
    after = runtime.context()
    health = runtime.health()
    transcript = runtime.drain("log")

    # Re-read after a further run, which is what makes this a regression test rather than a
    # snapshot: the summary lives in a `SystemPromptPart`, so a system-prompt manager that
    # rewrites the history would drop it on the way into that last request.
    assert summaries(after["messages"]), (
        "the summary was discarded by the next request, so every run re-summarizes"
    )
    assert not summaries(model_messages(transcript)), (
        "a summary is a compaction artifact and must never enter the raw transcript"
    )

    # The summary replaced a prefix the transcript still holds in full. How much of the tool
    # traffic survives in the context is the model's choice; whether the transcript keeps all of
    # it is not, and `tests/api/test_compaction.py` pins that deterministically.
    assert len(transcript) > len(summarized["messages"])

    # Five runs, but more than five commits: compaction fires between model requests, so a run
    # that compacts persists its context before it ends.
    assert health["context_version"] > FILLER_TURNS + 1

    # `keep_user_messages` also preserves the originating turn verbatim, so this does not
    # isolate the summary; it checks the weaker but essential property that heavy compaction on
    # every single request still leaves a conversation the model can answer from.
    assert "hello world" in recalled.reply.lower(), (
        f"compaction lost the conversation's own history; model replied {recalled.reply!r}"
    )
