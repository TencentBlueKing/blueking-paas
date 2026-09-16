"""What a run does to the Project's Git repository, from the outside.

Drives the real Runtime over HTTP with a fake model, against a real bare remote. These tests are
about the seam the plan cares about: a turn's stream ending means the files are *committed*, and
getting them to the remote is a separate, observable state the next turn can be made to wait for.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

from app_spark_agent import settings
from app_spark_agent.git import WorkspaceSaver
from app_spark_agent.server.runtime import ConversationRuntime
from tests.api.support import build_test_client, run_turn
from tests.git.conftest import BRANCH, clone_to, make_workspace, plain_git
from tests.support.ag_ui import SSE_HEADERS, run_body
from tests.support.fake_models import text_model

WRITE_TOOL = "write_note"

# Long enough to survive a loaded machine, short enough that a save that never lands fails the
# test instead of hanging the suite.
SAVE_TIMEOUT_SECONDS = 10.0


class ClientFactory(Protocol):
    """Build one started Runtime, saved to the shared remote, per call."""

    def __call__(self, *, note: str = ..., backoff: float = ...) -> TestClient: ...


@pytest.fixture(autouse=True)
def short_save_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink the pre-run gate's bounded wait, so its timeout is reached in test time."""
    monkeypatch.setattr(settings, "GIT_SAVE_WAIT_TIMEOUT_SECONDS", 0.2)


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """An empty bare repository standing in for the Project's remote."""
    remote = tmp_path / "remote.git"
    plain_git("init", "--bare", "--initial-branch", BRANCH, str(remote), cwd=tmp_path)
    return remote


@pytest.fixture
def make_client(tmp_path: Path, bare_remote: Path) -> Iterator[ClientFactory]:
    """Return a factory for Runtimes whose workspace is saved to ``bare_remote``.

    :param note: What the model's tool writes into the workspace during a turn.
    :param backoff: Push retry interval. Raised by tests that need a failure to *stay* failed
        long enough to be observed.
    """
    with ExitStack() as lifespans:

        def factory(*, note: str = "hello from the model", backoff: float = 0.01) -> TestClient:
            root = tmp_path / f"runtime-{uuid4().hex[:8]}"
            root.mkdir()
            client = build_test_client(
                root,
                model=file_writing_model(),
                tools=[note_writer(root / "workspace", note)],
                make_saver=lambda workspace: WorkspaceSaver(
                    make_workspace(workspace, bare_remote),
                    project_id="proj-42",
                    retry_backoff_seconds=backoff,
                ),
            )
            # Entering the client runs the lifespan, which is what attaches the workspace to its
            # remote before any run can touch a file.
            lifespans.enter_context(client)
            return client

        yield factory


def file_writing_model() -> FunctionModel:
    """A model that writes one file through a tool, then answers, then stops."""
    called = False

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str | DeltaToolCalls]:
        nonlocal called
        if called:
            yield "done"
            return
        called = True
        yield {0: DeltaToolCall(name=WRITE_TOOL, json_args=json.dumps({}), tool_call_id="call-1")}

    return FunctionModel(stream_function=stream)


def note_writer(workspace: Path, note: str) -> Callable[[], str]:
    """A tool that writes into the workspace, standing in for the real coding capabilities."""

    def write_note() -> str:
        (workspace / "note.txt").write_text(f"{note}\n")
        return "written"

    write_note.__name__ = WRITE_TOOL
    return write_note


def health(client: TestClient) -> dict[str, Any]:
    """Read the Runtime's health document."""
    response = client.get("/health")
    assert response.status_code == 200, response.text
    return dict(response.json())


def wait_for_saved(client: TestClient, *, timeout: float = SAVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Poll ``/health`` until the workspace is saved remotely, or fail the test."""
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = health(client)
        if not latest["workspace_save_pending"]:
            return latest
        time.sleep(0.02)
    raise AssertionError(f"the workspace was never saved: {latest.get('workspace')}")


class TestTurnIsCommittedAndPushed:
    def test_a_turn_that_wrote_a_file_lands_in_the_repository(
        self, make_client: ClientFactory, bare_remote: Path, tmp_path: Path
    ) -> None:
        client = make_client(note="written by a run")

        run_turn(client, conversation_id=str(uuid4()))

        saved = wait_for_saved(client)["workspace"]
        assert saved["state"] == "saved"
        assert saved["pushed_sha"] == saved["local_sha"]

        clone = clone_to(bare_remote, tmp_path / "clone")
        assert (clone / "note.txt").read_text() == "written by a run\n"

    def test_the_commit_names_the_run_and_conversation_it_came_from(
        self, make_client: ClientFactory, bare_remote: Path, tmp_path: Path
    ) -> None:
        client = make_client()
        conversation_id = str(uuid4())
        run_id = str(uuid4())

        run_turn(client, conversation_id=conversation_id, run_id=run_id)
        wait_for_saved(client)

        clone = clone_to(bare_remote, tmp_path / "clone")
        message = plain_git("log", "-1", "--format=%B", cwd=clone)
        assert f"Run-Id: {run_id}" in message
        assert f"Conversation-Id: {conversation_id}" in message
        assert "Project-Id: proj-42" in message
        assert "Turn-Status: completed" in message

    def test_a_turn_that_wrote_nothing_leaves_the_repository_alone(self, make_client: ClientFactory) -> None:
        client = make_client()
        conversation_id = str(uuid4())
        run_turn(client, conversation_id=conversation_id)
        first = wait_for_saved(client)["workspace"]["local_sha"]

        # The tool writes the same content again, so this turn changes no file at all.
        run_turn(client, conversation_id=conversation_id)

        assert wait_for_saved(client)["workspace"]["local_sha"] == first


class TestHealthReporting:
    def test_a_runtime_without_a_repository_says_so_rather_than_pretending(self, tmp_path: Path) -> None:
        # The distinction matters: "no repository configured" and "everything is saved" must not
        # look alike to anything deciding whether this Runtime is safe to discard.
        client = build_test_client(tmp_path, model=text_model(("hi",)))

        with client:
            document = health(client)

        assert document["workspace_persisted"] is False
        assert document["workspace"] is None

    def test_the_payload_carries_the_age_and_the_failure_count(self, make_client: ClientFactory) -> None:
        client = make_client()

        run_turn(client, conversation_id=str(uuid4()))

        workspace = wait_for_saved(client)["workspace"]
        assert workspace["unsaved_seconds"] == 0.0
        assert workspace["push_failures"] == 0
        assert workspace["needs_attention"] is False

    def test_an_unsaved_turn_is_reported_as_pending(self, make_client: ClientFactory, bare_remote: Path) -> None:
        client = make_client(backoff=60.0)
        conversation_id = str(uuid4())
        run_turn(client, conversation_id=conversation_id)
        wait_for_saved(client)
        moved = _take_remote_offline(bare_remote)
        try:
            _run_turn_changing_a_file(client, conversation_id=conversation_id, note="second")

            document = health(client)
            assert document["workspace_save_pending"] is True
            assert document["workspace"]["local_sha"] != document["workspace"]["pushed_sha"]
            assert document["workspace"]["unsaved_seconds"] >= 0.0
        finally:
            moved.rename(bare_remote)


class TestPreRunGate:
    def test_the_next_turn_is_refused_while_the_previous_one_is_unsaved(
        self, make_client: ClientFactory, bare_remote: Path
    ) -> None:
        client = make_client(backoff=60.0)
        conversation_id = str(uuid4())
        run_turn(client, conversation_id=conversation_id)
        wait_for_saved(client)
        moved = _take_remote_offline(bare_remote)
        try:
            _run_turn_changing_a_file(client, conversation_id=conversation_id, note="second")

            response = client.post("/runs", headers=SSE_HEADERS, json=_run_body(client, conversation_id))

            assert response.status_code == 409
            detail = response.json()["detail"]
            assert detail["code"] == "workspace_save_pending"
            assert detail["workspace"]["state"] in {"pending", "pushing", "failed"}
        finally:
            moved.rename(bare_remote)

    def test_the_caller_can_choose_to_continue_without_saving(
        self, make_client: ClientFactory, bare_remote: Path
    ) -> None:
        # The escape hatch. Without it a network partition would lock the user out of their own
        # conversation rather than merely failing to back it up.
        client = make_client(backoff=60.0)
        conversation_id = str(uuid4())
        run_turn(client, conversation_id=conversation_id)
        wait_for_saved(client)
        moved = _take_remote_offline(bare_remote)
        try:
            _run_turn_changing_a_file(client, conversation_id=conversation_id, note="second")

            response = client.post(
                "/runs?allow_unsaved=true",
                headers=SSE_HEADERS,
                json=_run_body(client, conversation_id),
            )

            assert response.status_code == 200, response.text
            # And the Runtime still says the work is unsaved: continuing is not pretending.
            assert health(client)["workspace_save_pending"] is True
        finally:
            moved.rename(bare_remote)

    def test_a_saved_workspace_does_not_delay_the_next_turn(self, make_client: ClientFactory) -> None:
        client = make_client()
        conversation_id = str(uuid4())
        run_turn(client, conversation_id=conversation_id)
        wait_for_saved(client)

        started = time.monotonic()
        run_turn(client, conversation_id=conversation_id)

        # Well under the gate's bounded wait: there was nothing outstanding to wait for.
        assert time.monotonic() - started < settings.GIT_SAVE_WAIT_TIMEOUT_SECONDS + 1.0


def _run_body(client: TestClient, conversation_id: str) -> dict[str, Any]:
    """One AG-UI run request body, for the tests that post it themselves.

    The version is read back rather than assumed: these bodies are posted after earlier turns
    have already moved it, and a stale version would be refused for the wrong reason.
    """
    return run_body(
        conversation_id=conversation_id,
        run_id=str(uuid4()),
        context_version=health(client)["context_version"],
        prompt="hello",
    )


def _run_turn_changing_a_file(client: TestClient, *, conversation_id: str, note: str) -> None:
    """Drive one turn that definitely changes a file, so something is left unsaved.

    The model's tool writes the same content every turn, so a second turn on its own would
    change nothing and leave the repository already up to date.
    """
    (_workspace_of(client) / "extra.txt").write_text(f"{note}\n")
    run_turn(client, conversation_id=conversation_id)


def _workspace_of(client: TestClient) -> Path:
    """The workspace directory behind a client, read back from the Runtime it serves."""
    runtime: ConversationRuntime = client.app.state.conversation_runtime  # type: ignore[union-attr]
    assert runtime.saver is not None
    return runtime.saver.workspace.path


def _take_remote_offline(bare_remote: Path) -> Path:
    """Move the remote aside, standing in for a host that stopped answering.

    :return: Where it went, so the test can put it back.
    """
    moved = bare_remote.parent / "remote-offline.git"
    bare_remote.rename(moved)
    return moved
