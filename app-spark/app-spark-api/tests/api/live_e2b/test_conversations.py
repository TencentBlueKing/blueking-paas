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

"""Drive E2B-backed chat and application preview through the authenticated API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from app_spark_api.agent.runtime.models import E2BSandboxRecord
from tests.agent.runtime.e2b_support import SANDBOX_WORKSPACE, logger
from tests.api.support import CONVERSATIONS_URL

if TYPE_CHECKING:
    from django.http import StreamingHttpResponse

pytestmark = [pytest.mark.e2b, pytest.mark.django_db(transaction=True)]
PREVIEW_MARKER = "e2b-preview-from-recorded-sandbox"


async def _create_conversation(client) -> dict:
    response = await client.post(CONVERSATIONS_URL)
    assert response.status_code == HTTPStatus.CREATED, response.content
    return json.loads(response.content)


async def _stream_body(response: StreamingHttpResponse) -> bytes:
    stream = response.streaming_content
    assert isinstance(stream, AsyncIterator)
    return b"".join([chunk async for chunk in stream])


async def test_chat_turn_runs_through_e2b_provider(aapi_client, project, e2b_provider):
    """The API creates an E2B sandbox and streams a real fake-model chat turn."""
    logger.info("Creating a conversation through the API")
    state = await _create_conversation(aapi_client)
    conversation_id = state["conversation_id"]
    sandbox = await e2b_provider.get_sandbox(conversation_id)
    assert sandbox is not None
    assert await E2BSandboxRecord.objects.active_for_conversation(conversation_id).aexists()
    assert state["model"] == "fake:write-file"

    logger.info("Posting chat turn and collecting AG-UI events")
    response = await aapi_client.post(
        f"{CONVERSATIONS_URL}{state['number']}/runs/",
        data={"content": "write an API test note"},
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers["content-type"] == "text/event-stream"
    body = await _stream_body(response)
    assert b"RUN_STARTED" in body
    assert b"RUN_FINISHED" in body
    assert b"TOOL_CALL_RESULT" in body
    assert "write an API test note" in await sandbox.files.read(f"{SANDBOX_WORKSPACE}/fake-agent-note-1.md")
    logger.info("Chat turn finished and the sandbox workspace contains the note")


async def test_preview_origin_proxies_to_fixed_e2b_port(aapi_client, project, e2b_provider):
    """The API's preview URL reaches the sandbox app through its fixed port host."""
    state = await _create_conversation(aapi_client)
    sandbox = await e2b_provider.get_sandbox(state["conversation_id"])
    assert sandbox is not None
    preview_dir = "/tmp/app-spark-preview"
    await sandbox.commands.run(f"mkdir -p {preview_dir}")
    await sandbox.files.write(f"{preview_dir}/index.html", PREVIEW_MARKER)
    await sandbox.commands.run(
        f"python3 -m http.server {e2b_provider.config.preview_port} "
        f"--bind 0.0.0.0 --directory {preview_dir} > /tmp/app-spark-preview.log 2>&1",
        background=True,
        timeout=0,
    )

    logger.info("Reading API preview origin for sandbox %s", sandbox.sandbox_id)
    metadata = await aapi_client.get(f"{CONVERSATIONS_URL}{state['number']}/preview/")
    assert metadata.status_code == HTTPStatus.OK, metadata.content
    origin = json.loads(metadata.content)["origin"]
    assert origin.endswith(f"{CONVERSATIONS_URL}{state['number']}/preview/app/")
    assert sandbox.get_host(e2b_provider.config.preview_port) not in origin

    preview_path = f"{CONVERSATIONS_URL}{state['number']}/preview/app/"
    for attempt in range(10):
        response = await aapi_client.get(preview_path)
        if response.status_code == HTTPStatus.OK:
            break
        if attempt == 9:
            pytest.fail(f"Preview app never became reachable: {response.status_code}")
        await asyncio.sleep(1)
    assert PREVIEW_MARKER.encode() in await _stream_body(response)
    logger.info("Preview URL proxied the sandbox application successfully")
