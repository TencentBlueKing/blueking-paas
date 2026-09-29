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

"""Listing a Project's conversations, and ending one of them.

Deliberately no agent here, unlike ``test_conversations.py``. Both operations are about the
conversation *row*: listing reads this service's own tables, and ending one is a database write
plus a best-effort attempt to stop a Runtime that, in these tests, was never started. Spawning
a real agent would only make them slow and require the agent's virtualenv.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from asgiref.sync import sync_to_async
from django.utils import timezone

from app_spark_api.agent.conversations import services, state
from app_spark_api.agent.conversations.entities import MAX_RUN_CONTENT_LENGTH
from app_spark_api.agent.conversations.history import DEFAULT_PAGE_RUNS, MAX_PAGE_RUNS
from app_spark_api.agent.conversations.models import (
    Conversation,
    ConversationUserMessage,
)
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from tests.api.support import CONVERSATIONS_URL, configure_local_provider, create_reachable_project
from tests.helpers import create_user

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def runtime_provider(settings, tmp_path: Path) -> None:
    """Give the provider somewhere harmless to point at.

    Ending a conversation goes through ``terminate_runtime()``, which needs a provider to exist
    even when there is no Runtime for it to stop.
    """
    configure_local_provider(settings, tmp_path)


@pytest.fixture
def project(bk_user) -> Project:
    return create_reachable_project(bk_user)


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


def close_url(number: int) -> str:
    return f"{CONVERSATIONS_URL}{number}/close/"


async def make_conversation(project: Project, owner: str) -> Conversation:
    """Add a conversation from inside an async test.

    Allocating a number takes a row lock and therefore a transaction, which the async ORM has
    none of -- so this goes through the service that already puts it on a worker thread, rather
    than reaching for the manager directly the way the sync fixtures above can.
    """
    return await services.create_conversation(project, owner=owner)


async def make_project(*, project_id: str, name: str, owner, tenant_id: str) -> Project:
    """Add a Project from inside an async test."""
    return await Project.objects.acreate(
        id=project_id,
        name=name,
        creator=owner,
        owner=owner,
        tenant_id=tenant_id,
    )


# --- listing ----------------------------------------------------------------------------


async def test_a_listed_conversation_carries_what_it_takes_to_open_it(aapi_client, conversation):
    body = (await aapi_client.get(CONVERSATIONS_URL)).json()

    assert body["count"] == 1
    (item,) = body["items"]
    assert item["number"] == conversation.number
    assert item["conversation_id"] == str(conversation.id)
    assert item["is_live"] is True
    assert item["closed_at"] is None


async def test_the_list_is_newest_first(aapi_client, project, bk_user):
    for index in range(3):
        created = await make_conversation(project, bk_user.pk)
        # `created_at` is auto_now_add, so conversations built back to back can share a timestamp
        # and leave the order down to the tiebreaker. Set explicitly, since the order is the
        # thing under test here.
        await Conversation.objects.filter(pk=created.pk).aupdate(created_at=datetime(2026, 1, index + 1, tzinfo=UTC))

    body = (await aapi_client.get(CONVERSATIONS_URL)).json()

    assert [item["number"] for item in body["items"]] == [3, 2, 1]


async def test_the_list_covers_one_project_only(aapi_client, project, conversation, bk_user):
    """Numbers restart per Project, so leaking across them would also be ambiguous."""
    elsewhere = await make_project(
        project_id="other-project",
        name="Other Project",
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )
    await make_conversation(elsewhere, bk_user.pk)

    body = (await aapi_client.get(CONVERSATIONS_URL)).json()

    assert [item["conversation_id"] for item in body["items"]] == [str(conversation.id)]


async def test_the_list_is_paginated_by_page_number(aapi_client, project, bk_user):
    for _ in range(3):
        await make_conversation(project, bk_user.pk)

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}?page=2&page_size=2")).json()

    assert len(body["items"]) == 1
    assert body["count"] == 3


async def test_a_project_nobody_in_this_tenant_owns_is_not_found(aapi_client, bk_user):
    await make_project(project_id="far-away", name="Far Away", owner=bk_user, tenant_id="some-other-tenant")

    response = await aapi_client.get("/api/projects/far-away/conversations/")

    assert response.status_code == HTTPStatus.NOT_FOUND


# --- reaching someone else's conversations ----------------------------------------------


@pytest.fixture
async def someone_elses_conversation(bk_user) -> Conversation:
    """A conversation of a Project that another user of the *same* tenant owns."""
    project = await make_project(
        project_id="not-mine",
        name="Not Mine",
        owner=create_user(),
        tenant_id=get_tenant(bk_user).id,
    )
    return await make_conversation(project, owner="somebody-else")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", ""),
        # Creating is in here too: it is the one read that provisions a Runtime, so reaching it
        # would spend someone else's workspace as well as look at their Project.
        ("post", ""),
        ("get", "{number}/"),
        ("get", "{number}/ui-events/"),
        ("get", "{number}/history/"),
        ("post", "{number}/close/"),
    ],
)
async def test_no_conversation_endpoint_reaches_another_users_project(
    aapi_client,
    someone_elses_conversation,
    method,
    path,
):
    """A tenant is not a boundary between users, so it cannot be the only thing checked.

    Closing is the reason this matters beyond privacy: it terminates a Runtime mid-run and hands
    back the workspace, so it would let anyone in the tenant destroy anyone else's work in
    progress by guessing nothing more than a ``project_id``.
    """
    url = f"/api/projects/not-mine/conversations/{path.format(number=someone_elses_conversation.number)}"

    response = await getattr(aapi_client, method)(url)

    assert response.status_code == HTTPStatus.NOT_FOUND
    # Never CONVERSATION_NOT_FOUND: naming the inner resource on the endpoints that take a
    # number would confirm the Project is there to be guessed at.
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
    await someone_elses_conversation.arefresh_from_db()
    assert someone_elses_conversation.is_live


# --- telling live from closed -----------------------------------------------------------


@pytest.fixture
async def one_live_and_one_closed(aapi_client, project, bk_user) -> tuple[Conversation, Conversation]:
    live = await make_conversation(project, bk_user.pk)
    closed = await make_conversation(project, bk_user.pk)
    await aapi_client.post(close_url(closed.number))
    return live, closed


async def test_the_list_can_be_narrowed_to_live_conversations(aapi_client, one_live_and_one_closed):
    live, _ = one_live_and_one_closed

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}?is_live=true")).json()

    assert [item["number"] for item in body["items"]] == [live.number]
    assert body["count"] == 1


async def test_the_list_can_be_narrowed_to_closed_conversations(aapi_client, one_live_and_one_closed):
    _, closed = one_live_and_one_closed

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}?is_live=false")).json()

    assert [item["number"] for item in body["items"]] == [closed.number]


async def test_the_unfiltered_list_keeps_both_and_says_which_is_which(aapi_client, one_live_and_one_closed):
    live, closed = one_live_and_one_closed

    body = (await aapi_client.get(CONVERSATIONS_URL)).json()

    assert {item["number"]: item["is_live"] for item in body["items"]} == {
        live.number: True,
        closed.number: False,
    }


# --- ending a conversation --------------------------------------------------------------


async def test_ending_a_conversation_reports_it_as_no_longer_live(aapi_client, conversation):
    response = await aapi_client.post(close_url(conversation.number))

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["is_live"] is False
    assert body["closed_at"] is not None
    assert body["conversation_id"] == str(conversation.id)

    await conversation.arefresh_from_db()
    assert conversation.closed_at is not None


async def test_ending_a_conversation_twice_is_refused(aapi_client, conversation):
    """Closing is a terminal transition, so the second call has nothing to do."""
    await aapi_client.post(close_url(conversation.number))

    response = await aapi_client.post(close_url(conversation.number))

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"code": "CONVERSATION_CLOSED", "detail": "This conversation has been closed."}


async def test_ending_a_conversation_revokes_its_runtimes_authority_to_write(aapi_client, conversation):
    """A Runtime this service lost track of must not be able to keep replicating state."""
    epoch_before = conversation.state_epoch

    await aapi_client.post(close_url(conversation.number))

    await conversation.arefresh_from_db()
    assert conversation.state_epoch == epoch_before + 1


async def test_a_runtime_that_refuses_to_stop_still_loses_its_authority_to_write(
    aapi_client,
    conversation,
    monkeypatch,
):
    """The half of the cleanup that has to land even when the other half fails.

    Stopping a process is best-effort, revoking is not -- and there is no second close to fall
    back on, since a repeat is refused. So a provider that cannot stop its Runtime must not be
    able to take the revocation down with it, or a Runtime nobody can reach would go on writing
    into a conversation that has already ended.
    """

    async def refuse_to_stop(conversation_id: str) -> None:
        raise RuntimeError("the Runtime is not listening")

    monkeypatch.setattr(get_agent_runtime_provider(), "terminate", refuse_to_stop)
    epoch_before = conversation.state_epoch

    response = await aapi_client.post(close_url(conversation.number))

    assert response.status_code == HTTPStatus.OK
    await conversation.arefresh_from_db()
    assert conversation.closed_at is not None
    assert conversation.state_epoch == epoch_before + 1


async def test_a_conversation_closed_while_its_runtime_comes_up_does_not_keep_it(
    aapi_client,
    conversation,
    monkeypatch,
):
    """The window between the gate on the run path and a Runtime actually being up.

    Bringing one up takes seconds, which is easily long enough for a close to land in the
    middle. Without a second check the closed conversation would come back with a Runtime
    holding the very workspace the close just handed back -- and one whose write-back token the
    close has already revoked, so the turn would run and then quietly fail to store anything.
    """
    terminated: list[str] = []

    async def close_it_behind_our_back(target: Conversation, **_: object) -> object:
        """Stand in for a concurrent close that lands after the gate has let this run past."""
        await Conversation.objects.filter(pk=target.pk).aupdate(closed_at=timezone.now())
        # The run is meant to be rejected before anything touches the client, so what this
        # hands back only has to be an object.
        return object()

    async def record_terminate(conversation_id: str) -> None:
        terminated.append(conversation_id)

    monkeypatch.setattr(services, "open_client", close_it_behind_our_back)
    monkeypatch.setattr(get_agent_runtime_provider(), "terminate", record_terminate)
    epoch_before = conversation.state_epoch

    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/",
        data={"content": "carry on"},
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.CONFLICT
    # The point is not that this request failed but that the Runtime it brought up was taken
    # back down, together with its authority to write.
    assert terminated == [str(conversation.id)]
    await conversation.arefresh_from_db()
    assert conversation.state_epoch == epoch_before + 1


async def test_a_closed_conversation_cannot_be_advanced(aapi_client, conversation):
    """Without this the close would be cosmetic: the next turn would respawn a Runtime."""
    await aapi_client.post(close_url(conversation.number))

    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/",
        data={"content": "carry on"},
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"code": "CONVERSATION_CLOSED", "detail": "This conversation has been closed."}


async def test_a_closed_conversation_still_reports_its_state(aapi_client, conversation):
    """The history stays readable; only advancing it is refused."""
    await aapi_client.post(close_url(conversation.number))

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/")).json()

    assert body["is_live"] is False
    assert body["closed_at"] is not None
    assert body["running"] is False


async def test_ending_a_conversation_that_does_not_exist_is_not_found(aapi_client, project):
    response = await aapi_client.post(close_url(404))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["code"] == "CONVERSATION_NOT_FOUND"


async def test_an_anonymous_caller_can_neither_list_nor_end(aanonymous_api_client, conversation):
    assert (await aanonymous_api_client.get(CONVERSATIONS_URL)).status_code == HTTPStatus.UNAUTHORIZED
    assert (await aanonymous_api_client.post(close_url(conversation.number))).status_code == (HTTPStatus.UNAUTHORIZED)


# --- what a turn may carry ---------------------------------------------------------------


async def test_an_oversized_turn_is_refused_before_it_reaches_the_database(aapi_client, conversation):
    """The body limit is 64MB for the Runtime's sake, so the turn needs a limit of its own.

    Without it a caller could park an arbitrarily large blob in ``ConversationUserMessage``,
    which is kept for the life of the conversation and read back whole on every history load.
    Also proves the check lands before the Runtime is spawned: there is no agent here, so
    anything that got past validation would fail differently.
    """
    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/",
        data={"content": "x" * (MAX_RUN_CONTENT_LENGTH + 1)},
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert not await ConversationUserMessage.objects.filter(conversation=conversation).aexists()


async def test_an_empty_turn_is_refused(aapi_client, conversation):
    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{conversation.number}/runs/",
        data={"content": ""},
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"


# --- paging back through the history ------------------------------------------------------
#
# The paging itself is pinned down in `tests/agent/conversations/test_history.py`; what is left
# for the endpoint is the contract a client actually codes against -- which end it starts from,
# what it hands back to keep going, and how a cursor it made up is answered.


async def seed_turns(conversation: Conversation, *turn_sizes: int) -> None:
    """Leave behind what completed turns leave behind, without an agent to produce them.

    The input goes in before its events, which is the real order and the only one that gives
    each input the ``after_seq`` the history reader positions it by.

    :param conversation: Conversation to advance.
    :param turn_sizes: One entry per turn, saying how many AG-UI events it produced.
    """

    def seed() -> None:
        for index, events in enumerate(turn_sizes, start=1):
            ConversationUserMessage.objects.create_for_conversation(conversation, content=f"turn-{index}")
            start = state.last_seq(conversation.id, state.UI_EVENT_CHANNEL) + 1
            state.append_records(
                conversation.id,
                state.UI_EVENT_CHANNEL,
                [
                    {
                        "seq": seq,
                        "run_id": f"run-{index}",
                        "timestamp": "2026-01-01T00:00:00+00:00",
                        "event": {"type": "CUSTOM", "n": seq},
                    }
                    for seq in range(start, start + events)
                ],
            )

    await sync_to_async(seed)()


def inputs_on(page: dict) -> list[str]:
    """The user's own lines on a page, which is the readable shape of "which turns are here"."""
    return [record["user_message"]["content"] for record in page["records"] if record["user_message"]]


async def test_the_first_history_page_is_the_newest_turns(aapi_client, conversation):
    """No cursor means the end of the conversation: that is where a returning reader resumes.

    Sized off the default rather than a literal count, so that tuning how much a page holds
    does not read as a regression here.
    """
    total = DEFAULT_PAGE_RUNS + 2
    await seed_turns(conversation, *([2] * total))

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/")).json()

    newest = range(total - DEFAULT_PAGE_RUNS + 1, total + 1)
    assert inputs_on(body) == [f"turn-{index}" for index in newest]
    assert body["next_cursor"] is not None
    # The channel's end, not this page's: it is the watermark a client then catches up from
    # over ui-events, so it must not follow the page backwards.
    assert body["last_seq"] == total * 2


async def test_the_cursor_walks_back_to_the_start_of_the_conversation(aapi_client, conversation):
    """Seeded past what one page holds, so this exercises the walk rather than a single read."""
    total = DEFAULT_PAGE_RUNS * 2 + 1
    await seed_turns(conversation, *([2] * total))
    url = f"{CONVERSATIONS_URL}{conversation.number}/history/"

    walked: list[str] = []
    visited = 0
    cursor = None
    for _ in range(total + 1):
        page = (await aapi_client.get(url, data={"cursor": cursor} if cursor else {})).json()
        walked = inputs_on(page) + walked
        visited += 1
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert cursor is None, "paging never reached the start of the conversation"
    assert visited > 1, "the whole conversation arrived in one page, so nothing was walked"
    assert walked == [f"turn-{index}" for index in range(1, total + 1)]


async def test_a_smaller_page_is_honoured(aapi_client, conversation):
    await seed_turns(conversation, 2, 2, 2)

    body = (await aapi_client.get(f"{CONVERSATIONS_URL}{conversation.number}/history/", data={"runs": 1})).json()

    assert inputs_on(body) == ["turn-3"]


async def test_a_history_cursor_this_service_did_not_issue_is_refused(aapi_client, conversation):
    """Named as its own failure rather than silently restarting at the newest page, which the

    client would experience as "load more does nothing".
    """
    response = await aapi_client.get(
        f"{CONVERSATIONS_URL}{conversation.number}/history/",
        data={"cursor": "made-up"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["code"] == "INVALID_HISTORY_CURSOR"


@pytest.mark.parametrize("runs", [0, -1, MAX_PAGE_RUNS + 1])
async def test_a_page_size_outside_the_allowed_range_is_refused(aapi_client, conversation, runs):
    """An upper bound as well as a lower one: a page carries whole tool-call arguments, so

    "give me every turn at once" is how a long conversation becomes a multi-megabyte response.
    """
    response = await aapi_client.get(
        f"{CONVERSATIONS_URL}{conversation.number}/history/",
        data={"runs": runs},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"
