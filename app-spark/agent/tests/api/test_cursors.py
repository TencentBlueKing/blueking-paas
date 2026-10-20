"""``PUT /cursors``: seeding a cold Runtime's numbering when there is no context to inject.

The control plane can hold a conversation's entries without any of its context, because the
channels are pushed first. The next Runtime still has to number after those entries, so this
is the half of ``PUT /context`` that does not need a document.
"""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.api.support import cold_context, drain_channel, run_in_flight, run_turn


def test_an_empty_runtime_continues_the_numbering_it_was_given(api: TestClient) -> None:
    """Without this, a replacement Runtime writes an entry 1 the control plane already has."""
    seeded = api.put("/cursors", params={"log_seq": 40, "ui_event_seq": 55})
    assert seeded.status_code == 200, seeded.text
    assert seeded.json() == {"log_seq": 40, "ui_event_seq": 55}

    run_turn(api, conversation_id=str(uuid4()))

    assert next(record["seq"] for record in drain_channel(api, "/log")) == 41
    assert next(record["seq"] for record in drain_channel(api, "/ui-events")) == 56


def test_the_seeded_history_is_reported_as_replicated(api: TestClient) -> None:
    """It came from the control plane, so a fresh Runtime must not look permanently behind."""
    api.put("/cursors", params={"log_seq": 40, "ui_event_seq": 55})

    reported: dict[str, Any] = api.get("/health").json()

    assert (reported["log_seq"], reported["ui_event_seq"]) == (40, 55)
    assert (reported["pushed_log_seq"], reported["pushed_ui_event_seq"]) == (40, 55)
    # No context came with it: the Runtime still adopts whichever conversation runs first.
    assert (reported["conversation_id"], reported["context_version"]) == (None, 0)


def test_seeding_the_same_cursors_twice_is_accepted(api: TestClient) -> None:
    """A retried request whose answer was lost must not look like a conflict."""
    params = {"log_seq": 40, "ui_event_seq": 55}

    assert api.put("/cursors", params=params).status_code == 200
    assert api.put("/cursors", params=params).status_code == 200


def test_a_runtime_that_already_wrote_history_refuses_to_be_renumbered(api: TestClient) -> None:
    run_turn(api, conversation_id=str(uuid4()))
    seqs_before = [record["seq"] for record in drain_channel(api, "/log")]

    refused = api.put("/cursors", params={"log_seq": 40, "ui_event_seq": 55})

    assert refused.status_code == 409
    assert [record["seq"] for record in drain_channel(api, "/log")] == seqs_before


def test_a_runtime_holding_a_conversation_refuses_to_be_renumbered(api: TestClient) -> None:
    """Its channels may still be empty, but its numbering already belongs to that conversation."""
    assert api.put("/context", json=cold_context(str(uuid4()))).status_code == 200

    refused = api.put("/cursors", params={"log_seq": 40, "ui_event_seq": 55})

    assert refused.status_code == 409
    assert "cannot be renumbered" in refused.json()["detail"]
    assert api.get("/health").json()["log_seq"] == 0


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"log_seq": -1, "ui_event_seq": 0}, id="negative"),
        pytest.param({"log_seq": 40}, id="missing-ui-event-seq"),
        pytest.param({"ui_event_seq": 55}, id="missing-log-seq"),
    ],
)
def test_incomplete_or_negative_cursors_are_rejected(api: TestClient, params: dict[str, int]) -> None:
    assert api.put("/cursors", params=params).status_code == 422
    assert api.get("/health").json()["log_seq"] == 0


async def test_seeding_is_refused_while_a_run_is_in_flight(tmp_path: Path) -> None:
    async with run_in_flight(tmp_path) as held:
        refused = await held.client.put("/cursors", params={"log_seq": 40, "ui_event_seq": 55})

        assert refused.status_code == 409
        assert "already in progress" in refused.json()["detail"]
        await held.release()
