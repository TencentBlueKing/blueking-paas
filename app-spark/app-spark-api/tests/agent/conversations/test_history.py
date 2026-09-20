# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Paging back through a conversation's display history.

What the tests are really about: a page boundary is only allowed to fall *between* turns. The
client replays a page by folding its events through a stateful reducer, so a page that starts in
the middle of a tool call renders a call that never finishes. Everything else here -- no gaps, no
duplicates, no drift while paging -- follows from the ordering key being append-only, and is
asserted against one reference read of the whole history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pytest

from app_spark_api.agent.conversations import history, state
from app_spark_api.agent.conversations.exceptions import InvalidHistoryCursorError
from app_spark_api.agent.conversations.models import Conversation, ConversationUserMessage
from app_spark_api.core.projects.models import Project

if TYPE_CHECKING:
    from app_spark_api.agent.conversations.entities import ConversationHistoryRecord

pytestmark = pytest.mark.django_db

TIMESTAMP = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def project(bk_user) -> Project:
    return Project.objects.create(
        id="history-paging",
        name="History Paging",
        creator=bk_user,
        owner=bk_user,
        tenant_id=bk_user.tenant_id,
    )


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


def add_turn(conversation: Conversation, *, content: str, events: int) -> str:
    """Leave behind what one completed turn leaves behind, in the order it really happens.

    The input lands first and takes its ``after_seq`` from wherever the event channel stands;
    the Runtime's events are replicated after. Doing it in that order is what makes these
    fixtures exercise the real ordering key rather than one the test made up.

    :param conversation: Conversation to advance.
    :param content: The user's input for this turn.
    :param events: How many AG-UI events the turn produced.
    :return: The run id the turn's events carry.
    """
    ConversationUserMessage.objects.create_for_conversation(conversation, content=content)
    start = state.last_seq(conversation.id, state.UI_EVENT_CHANNEL) + 1
    run_id = f"run-{start}"
    state.append_records(
        conversation.id,
        state.UI_EVENT_CHANNEL,
        [
            {"seq": seq, "run_id": run_id, "timestamp": TIMESTAMP, "event": {"type": "CUSTOM", "n": seq}}
            for seq in range(start, start + events)
        ],
    )
    return run_id


def identify(record: ConversationHistoryRecord) -> tuple[str, Any]:
    """Name one record so pages can be compared without carrying whole payloads around."""
    if record.ui_event is not None:
        return ("event", record.ui_event.seq)
    assert record.user_message is not None
    return ("input", record.user_message.content)


def read_all_pages(conversation: Conversation, *, runs: int = 1) -> list[list[tuple[str, Any]]]:
    """Page back to the beginning and return the pages oldest-first.

    Reversing here is what lets a test read like the conversation does: page 0 of the result is
    the start of the conversation, even though it was the last one fetched.

    :param conversation: Conversation to read.
    :param runs: Turns per page.
    :return: Each page's records, named by :func:`identify`, oldest page first.
    """
    pages: list[list[tuple[str, Any]]] = []
    cursor: str | None = None
    # Bounded so a cursor that fails to advance fails the test instead of hanging it.
    for _ in range(50):
        page = history.read_page(
            conversation,
            before_seq=history.decode_cursor(cursor) if cursor else None,
            runs=runs,
        )
        pages.append([identify(record) for record in page.records])
        cursor = page.next_cursor
        if cursor is None:
            return list(reversed(pages))
    pytest.fail("paging did not reach the start of the conversation")


# --- What one page holds --------------------------------------------------------------------


def test_the_first_page_holds_the_newest_turns(conversation) -> None:
    """Opening a conversation shows the end of it, which is where the reader left off."""
    add_turn(conversation, content="first", events=2)
    add_turn(conversation, content="second", events=2)
    add_turn(conversation, content="third", events=2)

    page = history.read_page(conversation, runs=2)

    assert [identify(record) for record in page.records] == [
        ("input", "second"),
        ("event", 3),
        ("event", 4),
        ("input", "third"),
        ("event", 5),
        ("event", 6),
    ]


def test_a_page_opens_with_the_input_that_began_its_oldest_turn(conversation) -> None:
    """The input sits at ``after_seq`` = the previous turn's last event, so it is a page's

    lower bound rather than something that falls off the front of it. Losing it would show a
    reply with no question above it.
    """
    add_turn(conversation, content="first", events=3)
    add_turn(conversation, content="second", events=3)

    page = history.read_page(conversation, runs=1)

    assert identify(page.records[0]) == ("input", "second")
    assert [identify(record) for record in page.records[1:]] == [("event", 4), ("event", 5), ("event", 6)]


def test_a_page_never_splits_a_turn(conversation) -> None:
    """The whole reason pages are counted in turns: a half-replayed tool call never finishes.

    Turns of deliberately unequal length, so a boundary that was really being placed by a count
    of records rather than a count of turns would have to land inside one of them.
    """
    for content, events in [("first", 4), ("second", 1), ("third", 7)]:
        add_turn(conversation, content=content, events=events)

    pages = read_all_pages(conversation, runs=1)

    assert pages == [
        [("input", "first"), *(("event", seq) for seq in range(1, 5))],
        [("input", "second"), ("event", 5)],
        [("input", "third"), *(("event", seq) for seq in range(6, 13))],
    ]


def test_the_last_turn_is_whole_too(conversation) -> None:
    add_turn(conversation, content="only", events=3)

    page = history.read_page(conversation, runs=1)

    assert [identify(record) for record in page.records] == [
        ("input", "only"),
        ("event", 1),
        ("event", 2),
        ("event", 3),
    ]
    assert page.next_cursor is None


# --- Walking the whole history ---------------------------------------------------------------


@pytest.mark.parametrize("runs", [1, 2, 3, 20])
def test_paging_back_covers_every_record_exactly_once(conversation, runs) -> None:
    """The property that makes this pagination usable at all: no gaps and no duplicates.

    It holds without a snapshot because the ordering key is append-only -- a new record's
    position is always past everything already stored, so nothing can appear inside a range
    that has already been handed out. Page size is varied because the boundaries move with it
    while the concatenation must not.
    """
    lengths = [2, 1, 5, 3, 1]
    expected: list[tuple[str, Any]] = []
    seq = 0
    for index, events in enumerate(lengths, start=1):
        add_turn(conversation, content=f"turn-{index}", events=events)
        expected.append(("input", f"turn-{index}"))
        expected.extend(("event", seq + offset) for offset in range(1, events + 1))
        seq += events

    walked = [record for page in read_all_pages(conversation, runs=runs) for record in page]

    assert walked == expected
    assert len(walked) == sum(lengths) + len(lengths)


def test_the_oldest_page_says_there_is_nothing_earlier(conversation) -> None:
    add_turn(conversation, content="first", events=2)
    add_turn(conversation, content="second", events=2)

    first = history.read_page(conversation, runs=1)
    assert first.next_cursor is not None
    oldest = history.read_page(conversation, before_seq=history.decode_cursor(first.next_cursor), runs=1)

    assert identify(oldest.records[0]) == ("input", "first")
    assert oldest.next_cursor is None


def test_each_page_hands_back_a_strictly_earlier_cursor(conversation) -> None:
    """What makes a client's "keep going until next_cursor is null" loop safe to write.

    A page that handed back the cursor it was given would spin forever on the same records, and
    the client has no way to tell that apart from a page that legitimately repeats.
    """
    for index in range(6):
        add_turn(conversation, content=f"turn-{index}", events=2)

    positions: list[int] = []
    cursor = history.read_page(conversation, runs=1).next_cursor
    while cursor is not None:
        before_seq = history.decode_cursor(cursor)
        positions.append(before_seq)
        cursor = history.read_page(conversation, before_seq=before_seq, runs=1).next_cursor

    # Every turn opens two events on, so each cursor is the opening event of the turn the next
    # page will start at. The walk stops after 3 rather than reaching 1: the page starting at
    # the second turn's opening event is the one that reads the first turn too, and it is that
    # page which reports there is nothing earlier.
    assert positions == [11, 9, 7, 5, 3]


def test_an_empty_conversation_reads_as_one_empty_page(conversation) -> None:
    page = history.read_page(conversation)

    assert page.records == []
    assert page.next_cursor is None
    assert page.last_seq == 0


# --- Inputs that never got a reply -----------------------------------------------------------


def test_inputs_sharing_a_position_stay_on_the_same_page(conversation) -> None:
    """Two inputs can share an ``after_seq``: a turn accepted but replicated no events leaves

    the channel where it was. A page boundary must not fall between them -- that is what the
    lower bound being the whole ``after_seq`` group, rather than one input, is for.
    """
    add_turn(conversation, content="first", events=3)
    ConversationUserMessage.objects.create_for_conversation(conversation, content="lost")
    add_turn(conversation, content="second", events=2)

    pages = read_all_pages(conversation, runs=1)

    assert pages == [
        [("input", "first"), ("event", 1), ("event", 2), ("event", 3)],
        [("input", "lost"), ("input", "second"), ("event", 4), ("event", 5)],
    ]


def test_an_input_still_waiting_for_its_events_is_on_the_newest_page(conversation) -> None:
    """Replication lands after the run's stream, so the newest turn is briefly input-only."""
    add_turn(conversation, content="first", events=2)
    ConversationUserMessage.objects.create_for_conversation(conversation, content="still running")

    page = history.read_page(conversation, runs=1)

    assert identify(page.records[-1]) == ("input", "still running")


def test_a_conversation_whose_events_never_arrived_reads_in_one_page(conversation) -> None:
    """Nothing to count turns by, so there is no earlier page to offer."""
    ConversationUserMessage.objects.create_for_conversation(conversation, content="first")
    ConversationUserMessage.objects.create_for_conversation(conversation, content="second")

    page = history.read_page(conversation, runs=1)

    assert [identify(record) for record in page.records] == [("input", "first"), ("input", "second")]
    assert page.next_cursor is None


# --- The event cap ---------------------------------------------------------------------------


def test_reaching_the_cap_costs_turns_rather_than_cutting_one(conversation, monkeypatch) -> None:
    """The cap is there for one runaway turn, so it must not damage ordinary ones on the way.

    Five events do not reach back over both turns, and the naive stop would leave the older
    turn's tail on this page without the input that opened it -- a fragment the client cannot
    replay. So the page gives back the turn it cannot complete instead.
    """
    monkeypatch.setattr(history, "MAX_PAGE_EVENTS", 5)
    add_turn(conversation, content="first", events=4)
    add_turn(conversation, content="second", events=4)

    pages = read_all_pages(conversation, runs=2)

    assert pages == [
        [("input", "first"), *(("event", seq) for seq in range(1, 5))],
        [("input", "second"), *(("event", seq) for seq in range(5, 9))],
    ]


def test_a_single_oversized_turn_is_cut_rather_than_sent_whole(conversation, monkeypatch) -> None:
    """The one case that does split a turn: not even one turn fits, so there is no boundary to

    fall back to. Paging stays correct -- the cursor only ever means "older than this position",
    it never claims to sit on a turn boundary -- so the guard costs page quality, not arithmetic.
    """
    monkeypatch.setattr(history, "MAX_PAGE_EVENTS", 3)
    add_turn(conversation, content="huge", events=8)

    pages = read_all_pages(conversation, runs=1)

    assert [len(page) for page in pages] == [3, 3, 3]
    assert [record for page in pages for record in page] == [("input", "huge")] + [
        ("event", seq) for seq in range(1, 9)
    ]


# --- What a page reports about the channel ---------------------------------------------------


def test_every_page_reports_the_channel_cursor_not_its_own(conversation) -> None:
    """It is the client's watermark for catching up forward over ui-events, so an older page

    must still report the end of the channel rather than the end of itself.
    """
    add_turn(conversation, content="first", events=2)
    add_turn(conversation, content="second", events=4)

    first = history.read_page(conversation, runs=1)
    assert first.next_cursor is not None
    older = history.read_page(conversation, before_seq=history.decode_cursor(first.next_cursor), runs=1)

    assert first.last_seq == older.last_seq == 6


def test_a_page_stays_inside_its_own_conversation(conversation, project, bk_user) -> None:
    neighbour = Conversation.objects.create_for_project(project, owner=bk_user.pk)
    add_turn(conversation, content="mine", events=2)
    add_turn(neighbour, content="theirs", events=2)

    page = history.read_page(conversation)

    assert [identify(record) for record in page.records] == [("input", "mine"), ("event", 1), ("event", 2)]


# --- The cursor ------------------------------------------------------------------------------


def test_a_cursor_round_trips() -> None:
    assert history.decode_cursor(history.encode_cursor(42)) == 42


def test_a_cursor_survives_a_url(conversation) -> None:
    """It travels as a query parameter, so it must not need escaping to get there."""
    add_turn(conversation, content="first", events=2)
    add_turn(conversation, content="second", events=2)

    cursor = history.read_page(conversation, runs=1).next_cursor

    assert cursor is not None
    assert cursor == quote(cursor, safe="")


@pytest.mark.parametrize(
    "cursor",
    [
        "not-base64-at-all!",
        # Well-formed base64 of a payload this service never issues.
        "aDA6NQ==",  # h0:5 -- a version that has been retired
        "NQ==",  # 5 -- the bare number, without the version prefix
        "aDE6",  # h1: -- the prefix with no position
        "aDE6LTE=",  # h1:-1
        "aDE6eA==",  # h1:x
    ],
)
def test_a_cursor_this_service_did_not_issue_is_refused(cursor) -> None:
    """Refused rather than treated as "start over": silently restarting looks to the client

    like "load more does nothing", with the real cause never stated.
    """
    with pytest.raises(InvalidHistoryCursorError):
        history.decode_cursor(cursor)
