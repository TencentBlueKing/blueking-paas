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

"""Driving conversations end to end against a real Agent Runtime process.

Nothing is mocked here. Every test spawns the actual agent, configured with the agent's own
``fake:`` model so the run costs nothing and always does the same thing, and drives it over
real HTTP. That is worth the seconds it takes: a fake provider would prove that this service
talks to a fake provider, whereas these prove the whole chain -- provisioning, the HTTP client,
the AG-UI passthrough, and the agent really writing to a workspace.

The replication half needs one more thing: this service has to be reachable from the spawned
Runtime, which is a separate process and cannot call an in-process test client. Hence
``live_server`` -- the Runtime pushes its state to a real socket, and the assertions read it
back out of the database through the ordinary async client.

Prerequisite: ``cd agent && uv sync``. Without the agent's virtualenv these tests skip with a
reason rather than failing in a way nobody can read.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from app_spark_api.agent.conversations import checkpoints
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.state_models import ConversationContextVersion
from app_spark_api.agent.runtime.factory import get_agent_runtime_provider
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.repository.git.services import provision_project_repository
from tests.infras.forgejo.fake import ORG, repo_server_config

if TYPE_CHECKING:
    from django.http import StreamingHttpResponse
    from django.test import AsyncClient

    from app_spark_api.agent.conversations.state_models import ConversationCheckpoint
    from app_spark_api.agent.runtime.providers.local import LocalProcessProvider

pytestmark = pytest.mark.django_db(transaction=True)

AGENT_PROJECT_DIR = Path(__file__).resolve().parents[3] / "agent"

PROJECT_ID = "spark-demo"

# What the agent's `fake:write-file` scenario writes, one per turn. It numbers the note by
# counting the user prompts in the history it was given, which makes the filename a direct
# assertion about whether the conversation's context really came back.
FIRST_NOTE = "fake-agent-note-1.md"
SECOND_NOTE = "fake-agent-note-2.md"

# How long to wait for the Runtime to finish pushing a turn. Replication is deliberately
# behind the run: the client is sent RUN_FINISHED as soon as the events are out, and the
# Runtime's own barrier is before it accepts another run, not before the client is told. So a
# read that follows a turn immediately is allowed to be a moment early, and these tests wait
# for the cursor to move rather than sleeping and hoping.
REPLICATION_TIMEOUT_SECONDS = 15.0
REPLICATION_POLL_INTERVAL_SECONDS = 0.05


@pytest.fixture
def git_remote_root(settings, fake_forgejo, tmp_path) -> Path:
    """Give the spawned Runtimes a Git remote that really exists.

    The shared fake Forgejo answers the provisioning API calls, but the ``clone_url`` it is
    configured with points nowhere -- which is right for tests that never start an Agent, and
    wrong for these. A Runtime here clones and pushes for real, so without a real repository
    behind the URL these tests would be asserting on a feature that could not work.

    A bare repository on disk is enough: what a local remote cannot reproduce is authentication
    and transport, and those are covered by the agent's own live-Forgejo tests.
    """
    root = tmp_path / "remotes"
    (root / ORG).mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch", "main", str(root / ORG / f"{PROJECT_ID}.git")],  # noqa: S607
        check=True,
        capture_output=True,
    )
    settings.REPO_SERVER = repo_server_config(clone_url=str(root))
    return root


@pytest.fixture
def project(bk_user, git_remote_root) -> Project:
    """A Project the logged-in user's tenant can reach.

    Deliberately not the shared ``project`` fixture: that one is created under the user's own
    random ``tenant_id``, while the API scopes by ``get_tenant()``, which is ``default`` unless
    multi-tenant mode is on.
    """
    project = Project.objects.create(
        id=PROJECT_ID,
        name="Spark Demo",
        creator=bk_user,
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )
    # Records the clone URL from `git_remote_root`, so the Runtime is pointed at the bare
    # repository that fixture created.
    provision_project_repository(project)
    return project


@pytest.fixture
def workspace_root(tmp_path) -> Path:
    return tmp_path / "workspaces"


@pytest.fixture
async def agent(settings, tmp_path, workspace_root, live_server) -> AsyncIterator[None]:
    """Point the service at the real agent, scripted with the free `write-file` scenario."""
    async for _ in _configured_agent(settings, tmp_path, workspace_root, live_server, "fake:write-file"):
        yield None


@pytest.fixture
async def slow_agent(settings, tmp_path, workspace_root, live_server) -> AsyncIterator[None]:
    """Point the service at an agent that keeps a run open long enough to collide with."""
    async for _ in _configured_agent(settings, tmp_path, workspace_root, live_server, "fake:slow"):
        yield None


@pytest.fixture
async def chat_agent(settings, tmp_path, workspace_root, live_server) -> AsyncIterator[None]:
    """Point the service at an agent that answers without changing workspace files."""
    async for _ in _configured_agent(settings, tmp_path, workspace_root, live_server, "fake:chat"):
        yield None


async def _configured_agent(
    settings: Any,
    tmp_path: Path,
    workspace_root: Path,
    live_server: Any,
    model: str,
) -> AsyncIterator[None]:
    """Configure the local provider, and make sure it leaves no process behind."""
    if not (AGENT_PROJECT_DIR / ".venv").exists():
        pytest.skip(f"The agent has no virtualenv yet; run `cd {AGENT_PROJECT_DIR} && uv sync`")

    # Archive contexts under the test's own directory rather than the shared default root.
    settings.AGENT_CONTEXT_STORAGE = {
        "backend": "host_tmp_path",
        "root": str(tmp_path / "agent-contexts"),
    }
    settings.AGENT_RUNTIME_PROVIDER = "local_process"
    settings.AGENT_RUNTIME_PROVIDER_CONFIG = {
        "agent_project_dir": str(AGENT_PROJECT_DIR),
        "workspace_root": str(workspace_root),
        "state_root": str(tmp_path / "agent-state"),
        # The spawned Runtime is a real process, so the only address it can push its state to
        # is a real one. Everything else in these tests goes through the in-process client.
        "callback_base_url": live_server.url,
        # Long enough that a second request lands while the run is still open, short enough
        # that a test which forgets to release it still finishes.
        "extra_env": {"APP_SPARK_AGENT_FAKE_DELAY_SECONDS": "5"},
    }
    # fake: 模型不发网络请求，也就用不着 bkaidev 的 access_token。
    settings.AGENT_MODEL_SOURCE = "direct"
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": model}
    try:
        yield None
    finally:
        # Before the `settings` fixture restores the old values: that would reset the cached
        # provider and leave the processes it started with nobody to stop them.
        await get_agent_runtime_provider().shutdown()


# --- Driving the API ---------------------------------------------------------------------


async def create_conversation(client: AsyncClient) -> dict[str, Any]:
    """Create a conversation and return the Runtime state it reports."""
    response = await client.post(f"/api/projects/{PROJECT_ID}/conversations/")
    assert response.status_code == HTTPStatus.CREATED, response.content
    return json.loads(response.content)


async def post_run(client: AsyncClient, number: int, prompt: str) -> Any:
    """Submit one turn without judging how it was answered."""
    return await client.post(
        f"/api/projects/{PROJECT_ID}/conversations/{number}/runs/",
        data={"content": prompt},
        content_type="application/json",
    )


async def run_turn(client: AsyncClient, number: int, prompt: str) -> list[dict[str, Any]]:
    """Submit one turn and read its event stream to the end."""
    response = await post_run(client, number, prompt)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers["content-type"] == "text/event-stream"
    return await collect_events(response)


async def collect_events(response: StreamingHttpResponse) -> list[dict[str, Any]]:
    """Parse a whole SSE body into the AG-UI events it carried."""
    # Django's async test client wraps the response in an async iterator; the sync half of the
    # declared union only happens under the sync client, which cannot reach these views at all.
    stream = response.streaming_content
    assert isinstance(stream, AsyncIterator)
    body = b"".join([chunk async for chunk in stream]).decode()
    return [
        json.loads(line.removeprefix("data:").strip())
        for line in body.replace("\r\n", "\n").splitlines()
        if line.startswith("data:")
    ]


def event_types(events: list[dict[str, Any]]) -> list[str]:
    return [str(event["type"]) for event in events]


def assistant_reply(events: list[dict[str, Any]]) -> str:
    """Reassemble the assistant's message from the deltas the client received."""
    return "".join(str(event["delta"]) for event in events if event.get("type") == "TEXT_MESSAGE_CONTENT")


async def read_state(client: AsyncClient, number: int) -> dict[str, Any]:
    """Read what this service knows about a conversation, without touching its Runtime."""
    response = await client.get(f"/api/projects/{PROJECT_ID}/conversations/{number}/")
    assert response.status_code == HTTPStatus.OK, response.content
    return json.loads(response.content)


async def read_ui_events(client: AsyncClient, number: int, since: int = 0) -> dict[str, Any]:
    """Read a page of a conversation's stored AG-UI history."""
    response = await client.get(
        f"/api/projects/{PROJECT_ID}/conversations/{number}/ui-events/",
        data={"since": since},
    )
    assert response.status_code == HTTPStatus.OK, response.content
    return json.loads(response.content)


async def read_history_page(client: AsyncClient, number: int, cursor: str | None = None) -> dict[str, Any]:
    """Read one page of a conversation's display history, newest page when no cursor is given."""
    query = {"cursor": cursor} if cursor else {}
    response = await client.get(f"/api/projects/{PROJECT_ID}/conversations/{number}/history/", data=query)
    assert response.status_code == HTTPStatus.OK, response.content
    return json.loads(response.content)


async def read_history(client: AsyncClient, number: int) -> list[dict[str, Any]]:
    """Page back through the whole display history and return it in conversation order.

    The endpoint hands out the *newest* page first, so the pages come back in reverse and are
    stitched by prepending. Tests assert about whole conversations, which is a different thing
    from what any one page holds; keeping the walk here is what keeps them readable.
    """
    records: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = await read_history_page(client, number, cursor)
        records = page["records"] + records
        cursor = page["next_cursor"]
        if cursor is None:
            return records


async def wait_for_replication(
    client: AsyncClient,
    number: int,
    *,
    after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wait until a finished turn has settled: pushed here, and the Runtime free again.

    The Runtime flushes before it releases its run guard, so a turn is briefly stored here
    while the Runtime still calls itself busy. Waiting for both makes "the turn is over" a
    single thing tests can ask for.

    Both flags are waited on, not just ``running``. A flush that timed out releases the run
    guard anyway, so ``running`` alone would let a test read the database while the Runtime is
    still ahead of it -- which is the flake this helper exists to prevent.

    :param after: The state read before the turn, if there was one. Every cursor has to move
        past it, which is what makes this a wait for *this* turn rather than the previous one.
    """
    floor = after or {"context_version": 0, "log_seq": 0, "ui_event_seq": 0}
    cursors = ("context_version", "log_seq", "ui_event_seq")
    deadline = time.monotonic() + REPLICATION_TIMEOUT_SECONDS
    while True:
        state = await read_state(client, number)
        idle = not state["running"] and not state["replication_pending"]
        if idle and all(state[cursor] > floor[cursor] for cursor in cursors):
            return state
        if time.monotonic() >= deadline:
            behind = {cursor: (floor[cursor], state[cursor]) for cursor in cursors}
            pytest.fail(
                f"The Runtime never settled its turn within {REPLICATION_TIMEOUT_SECONDS}s: "
                f"running={state['running']}, "
                f"replication_pending={state['replication_pending']}, cursors={behind}"
            )
        await asyncio.sleep(REPLICATION_POLL_INTERVAL_SECONDS)


async def wait_for_checkpoint(conversation_id: str) -> ConversationCheckpoint:
    """Wait until the last turn's commit is on the repository and reported here.

    A separate wait from :func:`wait_for_replication`, and deliberately so: the push runs behind
    the run's own barrier precisely so that a network round trip cannot hold up an answer to the
    user. "The turn is stored here" and "the turn is on the remote" are two different moments,
    and a restore needs the second one.
    """
    deadline = time.monotonic() + REPLICATION_TIMEOUT_SECONDS
    while True:
        checkpoint = await checkpoints.alatest(conversation_id)
        if checkpoint is not None:
            return checkpoint
        if time.monotonic() >= deadline:
            pytest.fail(f"No checkpoint appeared within {REPLICATION_TIMEOUT_SECONDS}s")
        await asyncio.sleep(REPLICATION_POLL_INTERVAL_SECONDS)


# --- The tests ---------------------------------------------------------------------------


async def test_a_new_conversation_comes_with_a_live_runtime(aapi_client, project, agent):
    state = await create_conversation(aapi_client)

    assert state["model"] == "fake:write-file"
    assert state["running"] is False
    assert state["context_version"] == 0
    # The number is what the caller will put in URLs; the UUID is what AG-UI events carry, so
    # both have to come back or the client cannot join the two together.
    assert state["number"] == 1
    assert await Conversation.objects.filter(id=state["conversation_id"], number=1).aexists()


async def test_a_turn_streams_agui_events_and_changes_the_workspace(
    aapi_client,
    project,
    agent,
    workspace_root,
):
    state = await create_conversation(aapi_client)

    events = await run_turn(aapi_client, state["number"], "write my first note")

    types = event_types(events)
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    # The agent reached for a real tool and the client saw it happen, delta by delta.
    assert "TOOL_CALL_START" in types
    assert "TOOL_CALL_RESULT" in types
    assert "TEXT_MESSAGE_CONTENT" in types
    assert FIRST_NOTE in assistant_reply(events)

    # And the workspace really changed, which is the whole point of driving an agent.
    note = workspace_root / PROJECT_ID / FIRST_NOTE
    assert note.exists()
    assert "write my first note" in note.read_text()


async def test_a_second_turn_continues_the_same_conversation(
    aapi_client,
    project,
    agent,
    workspace_root,
):
    state = await create_conversation(aapi_client)
    number = state["number"]

    await run_turn(aapi_client, number, "write my first note")
    first = await wait_for_replication(aapi_client, number)
    await run_turn(aapi_client, number, "write my second note")

    # A second note rather than a rewritten first one: the history the Runtime kept is what
    # told the agent this was turn two. Nothing about it was resent by this service.
    assert (workspace_root / PROJECT_ID / SECOND_NOTE).exists()

    # Both turns are in this service's storage, and the second one only added to the first.
    after = await wait_for_replication(aapi_client, number, after=first)
    assert after["context_version"] >= 2


async def test_missed_events_can_be_read_back_after_the_stream_is_gone(
    aapi_client,
    project,
    agent,
):
    state = await create_conversation(aapi_client)
    number = state["number"]
    streamed = await run_turn(aapi_client, number, "write my first note")
    await wait_for_replication(aapi_client, number)

    page = await read_ui_events(aapi_client, number)

    assert page["exhausted"] is True
    assert page["last_seq"] == len(page["records"]) > 0
    replayed = [record["event"]["type"] for record in page["records"]]
    assert replayed[0] == "RUN_STARTED"
    assert replayed[-1] == "RUN_FINISHED"
    # The history is the same run, with the per-token deltas already coalesced -- so it is
    # shorter than the live stream but tells the same story.
    assert len(replayed) <= len(streamed)


async def test_history_is_readable_without_waking_the_runtime(aapi_client, project, agent):
    """Opening an idle conversation must not cost a Runtime, however long its history is."""
    state = await create_conversation(aapi_client)
    number, conversation_id = state["number"], state["conversation_id"]
    await run_turn(aapi_client, number, "write my first note")
    await wait_for_replication(aapi_client, number)

    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)

    page = await read_ui_events(aapi_client, number)
    idle = await read_state(aapi_client, number)

    assert page["last_seq"] > 0
    history = await read_history(aapi_client, number)
    assert history[0]["ui_event"] is None
    assert history[0]["user_message"]["content"] == "write my first note"
    assert history[0]["user_message"]["run_id"] == page["records"][0]["run_id"]
    assert [row["ui_event"] for row in history if row["ui_event"] is not None] == page["records"]
    assert idle["running"] is False
    assert await provider.peek(conversation_id) is None


async def test_a_conversation_outlives_the_runtime_that_held_it(
    aapi_client,
    project,
    agent,
    workspace_root,
):
    """The real cold start: everything the Runtime knew is destroyed, and the talk goes on.

    Not just the process -- its state directory too, which is where the transcript, the AG-UI
    history and the context all lived. What comes back has to come back from this service.
    """
    state = await create_conversation(aapi_client)
    number, conversation_id = state["number"], state["conversation_id"]
    await run_turn(aapi_client, number, "write my first note")
    first = await wait_for_replication(aapi_client, number)

    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)
    shutil.rmtree(provider.state_dir(conversation_id))

    # The history survived a Runtime that no longer exists, in any form.
    before = await read_ui_events(aapi_client, number)
    assert before["records"][0]["event"]["type"] == "RUN_STARTED"

    await run_turn(aapi_client, number, "write my second note")

    # `fake:write-file` numbers its note by counting the user prompts it was given, so a second
    # note means the replacement Runtime was handed the first turn -- a Runtime starting from
    # nothing would have written the first note again.
    assert (workspace_root / PROJECT_ID / SECOND_NOTE).exists()

    # And the two Runtimes wrote into one flat sequence rather than colliding at seq 1: the
    # second generation was seeded with where the first one left off.
    after = await wait_for_replication(aapi_client, number, after=first)
    page = await read_ui_events(aapi_client, number)
    assert [record["seq"] for record in page["records"]] == list(range(1, after["ui_event_seq"] + 1))
    assert after["ui_event_seq"] > first["ui_event_seq"]
    history = await read_history(aapi_client, number)
    messages = [row["user_message"] for row in history if row["user_message"] is not None]
    assert [row["content"] for row in messages] == ["write my first note", "write my second note"]
    assert [row["after_seq"] for row in messages] == [0, first["ui_event_seq"]]
    # A restarted Runtime continues the same sequence; each input precedes its own reply.
    assert [(row["ui_event"] or row["user_message"])["run_id"] for row in history] == [messages[0]["run_id"]] * (
        first["ui_event_seq"] + 1
    ) + [messages[1]["run_id"]] * (after["ui_event_seq"] - first["ui_event_seq"] + 1)


async def test_a_destroyed_workspace_comes_back_from_its_checkpoint(
    aapi_client,
    project,
    agent,
    workspace_root,
):
    """The whole point of persisting to Git: the files outlive the machine they were written on.

    Everything the Runtime had is destroyed -- the process, its state directory, *and* the
    workspace itself. What comes back has to come back from two places at once: the files from
    the repository, the conversation from this service. Asserting on both together is what
    distinguishes a real restore from a Runtime that merely re-ran the first turn.
    """
    state = await create_conversation(aapi_client)
    number, conversation_id = state["number"], state["conversation_id"]
    await run_turn(aapi_client, number, "write my first note")
    first = await wait_for_replication(aapi_client, number)
    checkpoint = await wait_for_checkpoint(conversation_id)

    workspace = workspace_root / PROJECT_ID
    original = (workspace / FIRST_NOTE).read_text()
    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)
    shutil.rmtree(provider.state_dir(conversation_id))
    shutil.rmtree(workspace)

    await run_turn(aapi_client, number, "write my second note")

    # The first turn's file is back, byte for byte, from a commit the checkpoint pinned.
    assert (workspace / FIRST_NOTE).read_text() == original
    # And the second turn continued the conversation rather than restarting it, which is what
    # says the context came back alongside those files rather than instead of them.
    assert (workspace / SECOND_NOTE).exists()

    after = await wait_for_replication(aapi_client, number, after=first)
    assert after["context_version"] > checkpoint.context_version


async def test_a_context_only_conversation_cold_restores_and_keeps_advancing(
    aapi_client,
    project,
    chat_agent,
    workspace_root,
):
    """A conversation that never changed files needs no Git checkpoint to resume.

    Destroying the process, its state and its empty workspace makes the archived context the
    only place the first turn can come back from. The second turn advancing beyond the first
    version proves the replacement Runtime restored that context instead of starting at zero.
    """
    created = await create_conversation(aapi_client)
    number, conversation_id = created["number"], created["conversation_id"]

    first_events = await run_turn(aapi_client, number, "answer without editing files")
    first = await wait_for_replication(aapi_client, number)

    assert "You said: answer without editing files" in assistant_reply(first_events)
    assert await checkpoints.alatest(conversation_id) is None

    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)
    shutil.rmtree(provider.state_dir(conversation_id))
    shutil.rmtree(workspace_root / PROJECT_ID)

    second_events = await run_turn(aapi_client, number, "continue after the cold start")
    after = await wait_for_replication(aapi_client, number, after=first)

    assert "You said: continue after the cold start" in assistant_reply(second_events)
    assert after["context_version"] > first["context_version"]
    assert await checkpoints.alatest(conversation_id) is None
    workspace = workspace_root / PROJECT_ID
    assert not any(path for path in workspace.iterdir() if path.name != ".git")


async def test_cold_restore_after_file_edit_followed_by_context_only_turn(
    aapi_client,
    project,
    agent,
    settings,
    workspace_root,
):
    """A conversation that edits files and then has a chat-only turn still cold-restores.

    1. Turn 1 (`fake:write-file`) modifies the workspace -> creates Git checkpoint at
       `context_version == 1` and archives context v1.
    2. Turn 2 (`fake:chat`) answers without modifying any tracked/untracked files ->
       `context_version` advances to 2 while the latest workspace checkpoint stays at v1.
    3. The sandbox is reclaimed (process terminated, `state_dir` and `workspace` wiped).
    4. Turn 3 cold-restores both the Turn 1 files from Git and the Turn 2 context from storage.
    """
    created = await create_conversation(aapi_client)
    number, conversation_id = created["number"], created["conversation_id"]

    # Turn 1: writes `fake-agent-note-1.md`, producing context v1 + checkpoint v1.
    await run_turn(aapi_client, number, "write my first note")
    first = await wait_for_replication(aapi_client, number)
    first_checkpoint = await wait_for_checkpoint(conversation_id)
    assert first["context_version"] == 1
    assert first_checkpoint.context_version == 1

    workspace = workspace_root / PROJECT_ID
    original = (workspace / FIRST_NOTE).read_text()

    # Turn 2 needs a model that does not edit files, and the model is read when the Runtime
    # process starts -- so this terminate only restarts the process under `fake:chat`. Unlike
    # the reclamation below, `state_dir` and `workspace` are kept, so the restarted Runtime
    # picks up where it was rather than cold-restoring.
    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)
    settings.AGENT_DIRECT_MODEL_CONFIG = {"model": "fake:chat"}

    second_events = await run_turn(aapi_client, number, "just explain the code without editing")
    assert "You said: just explain the code without editing" in assistant_reply(second_events)
    second = await wait_for_replication(aapi_client, number, after=first)
    assert second["context_version"] == 2

    # Simulate Cube sandbox reclamation: process, state_dir, and workspace are all gone.
    await provider.terminate(conversation_id)
    shutil.rmtree(provider.state_dir(conversation_id))
    shutil.rmtree(workspace)

    # Turn 3 after sandbox reclamation: cold restore succeeds, bringing back Turn 1's file and
    # Turn 2's conversation context.
    third_events = await run_turn(aapi_client, number, "continue after sandbox reclamation")
    assert "You said: continue after sandbox reclamation" in assistant_reply(third_events)
    assert (workspace / FIRST_NOTE).read_text() == original
    third = await wait_for_replication(aapi_client, number, after=second)
    assert third["context_version"] == 3


async def test_a_first_turn_whose_context_never_arrived_keeps_one_flat_history(
    aapi_client,
    project,
    agent,
    workspace_root,
):
    """The Runtime is lost after its entries and commit were stored, but before its context was.

    The channels are pushed before the context, so this is what losing a Runtime during a
    conversation's first turn leaves behind. With no context to inject, the replacement still
    has to be told where the numbering stands: starting again at seq 1 would have its first
    entries dropped here as redeliveries of the ones already stored, while the live stream
    showed them -- a turn the history could never replay.
    """
    state = await create_conversation(aapi_client)
    number, conversation_id = state["number"], state["conversation_id"]
    await run_turn(aapi_client, number, "write my first note")
    first = await wait_for_replication(aapi_client, number)
    await wait_for_checkpoint(conversation_id)

    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    await provider.terminate(conversation_id)
    # Stopped first: a Runtime drains on SIGTERM, and would otherwise push the context again.
    await ConversationContextVersion.objects.filter(conversation_id=conversation_id).adelete()
    shutil.rmtree(provider.state_dir(conversation_id))
    shutil.rmtree(workspace_root / PROJECT_ID)

    second_events = await run_turn(aapi_client, number, "write another note")

    # The context is gone, so the second Runtime starts a new one from version 0.
    after = await wait_for_replication(aapi_client, number, after={**first, "context_version": 0})
    page = await read_ui_events(aapi_client, number)
    first_count, total = first["ui_event_seq"], after["ui_event_seq"]
    assert [record["seq"] for record in page["records"]] == list(range(1, total + 1))
    # The second turn is stored whole, from its own RUN_STARTED on, rather than only the tail
    # that happened to number past the first turn.
    assert page["records"][first_count]["event"]["type"] == "RUN_STARTED"
    assert page["records"][-1]["event"]["type"] == "RUN_FINISHED"
    second_run_id = page["records"][-1]["run_id"]
    assert [record["run_id"] for record in page["records"][first_count:]] == [second_run_id] * (total - first_count)
    assert event_types(second_events)[0] == "RUN_STARTED"
    history = await read_history(aapi_client, number)
    messages = [row["user_message"] for row in history if row["user_message"] is not None]
    assert [row["after_seq"] for row in messages] == [0, first_count]


async def test_a_turn_is_refused_while_another_is_still_running(
    aapi_client,
    project,
    slow_agent,
):
    state = await create_conversation(aapi_client)
    number = state["number"]

    # `fake:slow` emits a chunk and then stalls, so reading one chunk proves the run is under
    # way rather than merely submitted -- no sleeping and hoping.
    first = await post_run(aapi_client, number, "take your time")
    assert first.status_code == HTTPStatus.OK
    assert await anext(aiter(first.streaming_content))

    second = await post_run(aapi_client, number, "and me too")

    assert second.status_code == HTTPStatus.CONFLICT
    assert json.loads(second.content)["detail"] == (
        "The Agent Runtime is already executing a run for this conversation."
    )


class BrowserReading:
    """Reads a run's SSE the way a browser tab does, and can be closed the way one is.

    Closing cancels the reading task, which is what Django's ASGI handler does to a streaming
    response whose client disconnected: the cancellation lands on whatever the stream was
    awaiting -- here, the next bytes from the Runtime.
    """

    def __init__(self, response: Any) -> None:
        self.events: list[dict[str, Any]] = []
        self._started = asyncio.Event()
        self._task = asyncio.create_task(self._read(response.streaming_content))

    async def _read(self, stream: AsyncIterator[bytes]) -> None:
        async for chunk in stream:
            self.events.extend(
                json.loads(line.removeprefix("data:").strip())
                for line in chunk.decode().replace("\r\n", "\n").splitlines()
                if line.startswith("data:")
            )
            self._started.set()

    async def started(self) -> str:
        """Wait for the first event and return the run id it carries."""
        await asyncio.wait_for(self._started.wait(), REPLICATION_TIMEOUT_SECONDS)
        assert self.events[0]["type"] == "RUN_STARTED"
        return str(self.events[0]["runId"])

    async def finished(self) -> list[dict[str, Any]]:
        await asyncio.wait_for(self._task, REPLICATION_TIMEOUT_SECONDS)
        return self.events

    async def close(self) -> None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task


async def test_a_turn_runs_to_its_end_after_the_browser_goes_away(aapi_client, project, slow_agent):
    """Reloading the page used to cancel the turn mid-way, losing its context with it."""
    state = await create_conversation(aapi_client)
    number = state["number"]

    browser = BrowserReading(await post_run(aapi_client, number, "take your time"))
    await browser.started()
    # `fake:slow` is stalled after its first chunk, so this lands while the turn is under way.
    await browser.close()

    settled = await wait_for_replication(aapi_client, number, after=state)

    # A context version is only committed by a turn that got to its end.
    assert settled["context_version"] == 1
    records = (await read_ui_events(aapi_client, number))["records"]
    assert records[-1]["event"]["type"] == "RUN_FINISHED"
    assert "Thinking about: take your time" in assistant_reply([record["event"] for record in records])


async def test_a_turn_can_be_stopped_while_it_runs(aapi_client, project, slow_agent):
    state = await create_conversation(aapi_client)
    number = state["number"]
    stop_url = f"/api/projects/{PROJECT_ID}/conversations/{number}/runs/{{run_id}}/stop/"

    browser = BrowserReading(await post_run(aapi_client, number, "never mind"))
    run_id = await browser.started()
    # A client that reloaded has no SSE to read the run id from; the state carries it.
    assert (await read_state(aapi_client, number))["run_id"] == run_id

    stopped = await aapi_client.post(stop_url.format(run_id=run_id))

    assert stopped.status_code == HTTPStatus.ACCEPTED, stopped.content
    assert json.loads(stopped.content) == {"run_id": run_id}
    # The stream ends the way a finished turn's does, long before the stalled model would have.
    assert event_types(await browser.finished())[-1] == "RUN_FINISHED"
    settled = await wait_for_replication(aapi_client, number, after=state)
    # Stopped is not lost: what the turn did is part of the context the next one is given.
    assert settled["context_version"] == 1
    assert settled["run_id"] is None

    # Over now, so there is nothing to stop -- and a run this conversation never had is not one.
    again = await aapi_client.post(stop_url.format(run_id=run_id))
    assert again.status_code == HTTPStatus.CONFLICT, again.content
    assert json.loads(again.content)["code"] == "RUN_NOT_RUNNING"
    unknown = await aapi_client.post(stop_url.format(run_id="not-a-run-of-this-conversation"))
    assert unknown.status_code == HTTPStatus.NOT_FOUND, unknown.content
    assert json.loads(unknown.content)["code"] == "RUN_NOT_FOUND"


async def test_a_second_conversation_on_one_project_is_refused(aapi_client, project, agent):
    """Two agents in one workspace would edit the same files, so the second is turned away."""
    await create_conversation(aapi_client)

    response = await aapi_client.post(f"/api/projects/{PROJECT_ID}/conversations/")

    assert response.status_code == HTTPStatus.CONFLICT
    assert json.loads(response.content)["detail"] == (
        "Another conversation already has a running Agent on this project."
    )


async def test_ending_a_conversation_hands_the_project_back(aapi_client, project, agent):
    """The counterpart of the refusal above, and the reason ending a conversation exists.

    Nothing else reclaims a Runtime, so without this a Project would be stuck on its first
    conversation for as long as this service stayed up.

    Asserted against a real process rather than through the API alone: the point of closing is
    that the Runtime is actually gone, and a test that only read ``is_live`` back would pass
    just as well if the row were marked and the process left running.
    """
    first = await create_conversation(aapi_client)
    provider = cast("LocalProcessProvider", get_agent_runtime_provider())
    assert await provider.peek(first["conversation_id"]) is not None

    closed = await aapi_client.post(f"/api/projects/{PROJECT_ID}/conversations/{first['number']}/close/")

    assert closed.status_code == HTTPStatus.OK
    assert json.loads(closed.content)["is_live"] is False
    assert await provider.peek(first["conversation_id"]) is None

    # And the freed workspace is genuinely usable again, which is what the caller came for.
    second = await create_conversation(aapi_client)
    assert second["number"] == first["number"] + 1


async def test_anonymous_callers_are_refused(aanonymous_api_client, project):
    response = await aanonymous_api_client.post(f"/api/projects/{PROJECT_ID}/conversations/")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_a_project_of_another_tenant_is_not_found(aapi_client, project, settings):
    settings.ENABLE_MULTI_TENANT_MODE = True

    response = await aapi_client.post(f"/api/projects/{PROJECT_ID}/conversations/")

    assert response.status_code == HTTPStatus.NOT_FOUND
