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

"""What the client sends, and what it does when the answer is not a healthy Runtime's.

The happy paths are covered by ``tests/api/test_conversations.py``, which drives a real agent
process. What a healthy agent cannot be asked to do is misbehave, so the answers here are
staged with ``MockTransport`` -- httpx's own seam, which lets a test dictate a reply without a
socket, a port, or a server thread anywhere in sight.

The one exception is the dead port below, which starts nothing either but is a genuine
OS-level connection refusal rather than an assumption about which exception httpx would raise.
"""

from __future__ import annotations

import json
import socket

import httpx2
import pytest

from app_spark_api.agent.runtime.client import AgentRuntimeClient
from app_spark_api.agent.runtime.entities import AgentRuntimeHandle
from app_spark_api.agent.runtime.exceptions import AgentBusyError, AgentUnavailableError

CONVERSATION_ID = "6f1c5f6e-0a5d-4f4a-9a1e-1f4f0f2b3c4d"
RUNTIME_TOKEN = "runtime-token-for-client-tests"
HANDLE = AgentRuntimeHandle(
    conversation_id=CONVERSATION_ID,
    base_url="http://runtime.invalid",
    runtime_token=RUNTIME_TOKEN,
)

Route = tuple[int, bytes]


def runtime_answering(routes: dict[str, Route], recorder: list[httpx2.Request] | None = None) -> AgentRuntimeClient:
    """Return a client whose Runtime answers exactly what the test dictates.

    :param routes: Path to the ``(status, body)`` it should be answered with.
    :param recorder: Collects the requests as they are sent, for tests that care what was said
        rather than what came back.
    """

    def handle(request: httpx2.Request) -> httpx2.Response:
        if recorder is not None:
            recorder.append(request)
        status, body = routes.get(request.url.path, (404, b'{"detail":"no such route"}'))

        # Handed over as an async iterable rather than as bytes: a Response built from bytes
        # arrives already consumed, and `/runs` is read as a stream.
        async def body_stream():
            yield body

        return httpx2.Response(status, content=body_stream(), headers={"Content-Type": "application/json"})

    return AgentRuntimeClient(HANDLE, transport=httpx2.MockTransport(handle))


@pytest.fixture
def dead_handle() -> AgentRuntimeHandle:
    """A handle pointing at a port that has just been given up.

    This is what a Runtime that died, or was never spawned, looks like from here.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return AgentRuntimeHandle(
        conversation_id=CONVERSATION_ID,
        base_url=f"http://127.0.0.1:{port}",
        runtime_token=RUNTIME_TOKEN,
    )


# --- What the client sends ----------------------------------------------------------------


async def test_a_turn_is_submitted_as_one_new_agui_message():
    """The Runtime owns the history, so a turn carries the new message and nothing else."""
    sent: list[httpx2.Request] = []
    client = runtime_answering({"/runs": (200, b"data: {}\n\n")}, recorder=sent)

    run = await client.start_run(content="write my first note", context_version=7)

    body = json.loads(sent[0].content)
    assert body["threadId"] == CONVERSATION_ID
    assert body["runId"] == run.run_id
    assert body["forwardedProps"]["contextVersion"] == 7
    assert [(m["role"], m["content"]) for m in body["messages"]] == [("user", "write my first note")]
    assert sent[0].headers["accept"] == "text/event-stream"
    assert sent[0].headers["authorization"] == f"Bearer {RUNTIME_TOKEN}"


async def test_every_runtime_client_request_uses_the_handle_bearer():
    sent: list[httpx2.Request] = []
    client = runtime_answering(
        {
            "/health": (
                200,
                json.dumps(
                    {
                        "model": "fake:write-file",
                        "conversation_id": None,
                        "context_version": 0,
                        "log_seq": 0,
                        "ui_event_seq": 0,
                        "running": False,
                    }
                ).encode(),
            ),
            "/ui-events": (200, b'{"since": 0, "last_seq": 0, "records": []}'),
            "/runs": (200, b"data: {}\n\n"),
        },
        recorder=sent,
    )

    await client.health()
    await client.read_ui_events()
    run = await client.start_run(content="hello", context_version=0)
    await run.aclose()

    assert [request.headers["authorization"] for request in sent] == [
        f"Bearer {RUNTIME_TOKEN}",
        f"Bearer {RUNTIME_TOKEN}",
        f"Bearer {RUNTIME_TOKEN}",
    ]


async def test_each_turn_gets_its_own_run_id():
    """The Runtime refuses a replayed one, so the id cannot be reused between turns."""
    client = runtime_answering({"/runs": (200, b"data: {}\n\n")})

    first = await client.start_run(content="one", context_version=0)
    second = await client.start_run(content="two", context_version=0)

    assert first.run_id != second.run_id


async def test_the_accepted_stream_is_forwarded_byte_for_byte():
    """Nothing here parses AG-UI: whatever the Runtime wrote is what the caller gets."""
    stream = b'data: {"type":"RUN_STARTED"}\n\ndata: {"type":"RUN_FINISHED"}\n\n'
    client = runtime_answering({"/runs": (200, stream)})

    run = await client.start_run(content="hello", context_version=0)

    assert b"".join([chunk async for chunk in run.aiter_bytes()]) == stream


async def test_a_cursor_is_passed_through_to_the_drain():
    sent: list[httpx2.Request] = []
    client = runtime_answering(
        {"/ui-events": (200, b'{"since": 3, "last_seq": 4, "records": [{"seq": 4}]}')},
        recorder=sent,
    )

    page = await client.read_ui_events(since=3, limit=10)

    assert dict(sent[0].url.params) == {"since": "3", "limit": "10"}
    assert page.exhausted is True


# --- What the client does when the answer is wrong -----------------------------------------


async def test_health_reports_a_runtime_that_is_not_listening(dead_handle):
    with pytest.raises(AgentUnavailableError, match="Could not reach"):
        await AgentRuntimeClient(dead_handle).health()


async def test_reading_events_reports_a_runtime_that_is_not_listening(dead_handle):
    with pytest.raises(AgentUnavailableError, match="Could not reach"):
        await AgentRuntimeClient(dead_handle).read_ui_events()


async def test_starting_a_run_reports_a_runtime_that_is_not_listening(dead_handle):
    with pytest.raises(AgentUnavailableError, match="Could not start a run"):
        await AgentRuntimeClient(dead_handle).start_run(content="hello", context_version=0)


async def test_a_non_json_body_is_reported_as_such():
    client = runtime_answering({"/health": (200, b"<html>502 Bad Gateway</html>")})

    with pytest.raises(AgentUnavailableError, match="non-JSON"):
        await client.health()


async def test_an_unexpected_status_is_reported_with_the_bodys_explanation():
    client = runtime_answering({"/ui-events": (500, b'{"detail":"state directory is gone"}')})

    with pytest.raises(AgentUnavailableError, match="state directory is gone"):
        await client.read_ui_events(since=3, limit=10)


async def test_a_refused_run_carries_the_runtimes_own_reason():
    """A 409 is the one refusal with a meaning of its own, and it keeps its own exception type."""
    client = runtime_answering({"/runs": (409, b'{"detail":"a run is already in progress"}')})

    with pytest.raises(AgentBusyError, match="a run is already in progress"):
        await client.start_run(content="hello", context_version=1)


async def test_any_other_refusal_is_not_mistaken_for_a_busy_runtime():
    client = runtime_answering({"/runs": (422, b'{"detail":"contextVersion is stale"}')})

    with pytest.raises(AgentUnavailableError, match="contextVersion is stale") as exc_info:
        await client.start_run(content="hello", context_version=1)
    assert not isinstance(exc_info.value, AgentBusyError)


async def test_a_refusal_that_is_not_json_still_says_something_useful():
    client = runtime_answering({"/runs": (503, b"upstream connect error")})

    with pytest.raises(AgentUnavailableError, match="upstream connect error"):
        await client.start_run(content="hello", context_version=1)
