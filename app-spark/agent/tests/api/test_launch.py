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

"""POST /app/launch: start the workspace application and persist app.launched."""

import asyncio
import socket
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app_spark_agent import settings
from tests.api.support import (
    ApiFactory,
    drain_channel,
    http_client,
    post_run_async,
    wait_until_busy,
)
from tests.support.fake_models import gated_model

MINIMAL_APP = """
import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict[str, str]:
    return {"port": os.environ["APP_SPARK_AGENT_APP_PORT"]}
"""


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def workspace_of(client: TestClient) -> Path:
    return Path(client.app.state.conversation_runtime.app_supervisor.workspace)


def write_minimal_app(workspace: Path) -> None:
    (workspace / "main.py").write_text(MINIMAL_APP)


def launched_events(client: TestClient) -> list[dict[str, Any]]:
    return [
        record["event"]
        for record in drain_channel(client, "/ui-events")
        if record["event"].get("name") == "app.launched"
    ]


@pytest.fixture
def launch_port(monkeypatch: pytest.MonkeyPatch) -> int:
    port = unused_port()
    monkeypatch.setattr(settings, "APP_PORT", port)
    monkeypatch.setattr(settings, "PREVIEW_BASE_URL", "")
    return port


def test_launch_requires_bearer(api: TestClient) -> None:
    resp = TestClient(api.app).post("/app/launch", json={})
    assert resp.status_code == 401


def test_launch_rejects_an_illegal_path(api: TestClient) -> None:
    resp = api.post("/app/launch", json={"path": "../secret"})
    assert resp.status_code == 422
    assert api.get("/health").json()["app_status"] == "not_started"


def test_launch_rejects_a_foreign_port(api: TestClient, launch_port: int) -> None:
    write_minimal_app(workspace_of(api))
    occupant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupant.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    occupant.bind(("127.0.0.1", launch_port))
    occupant.listen(1)
    try:
        resp = api.post("/app/launch", json={})
        assert resp.status_code == 409
        assert api.get("/health").json()["app_status"] == "not_started"
        assert launched_events(api) == []
    finally:
        occupant.close()


def test_launch_starts_the_app_and_records_the_event(api: TestClient, launch_port: int) -> None:
    write_minimal_app(workspace_of(api))

    resp = api.post("/app/launch", json={})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["port"] == launch_port
    assert body["path"] == "/"
    assert body["label"] == "Preview"
    assert body["app_status"] == "healthy"
    assert body["url"] == f"http://127.0.0.1:{launch_port}/"

    opened = httpx.get(body["url"])
    assert 200 <= opened.status_code < 400
    assert opened.json()["port"] == str(launch_port)
    assert api.get("/health").json()["app_status"] == "healthy"

    events = launched_events(api)
    assert len(events) == 1
    assert events[0]["type"] == "CUSTOM"
    assert events[0]["value"] == {
        "port": launch_port,
        "path": "/",
        "label": "Preview",
        "url": body["url"],
    }


def test_relaunch_restarts_the_process(api: TestClient, launch_port: int) -> None:
    workspace = workspace_of(api)
    write_minimal_app(workspace)
    first = api.post("/app/launch", json={"path": "/"}).json()

    second = api.post("/app/launch", json={})

    assert second.status_code == 200
    assert second.json()["path"] == "/"
    opened = httpx.get(first["url"])
    assert 200 <= opened.status_code < 400


async def test_launch_is_allowed_during_a_run(make_api: ApiFactory, launch_port: int) -> None:
    gate = asyncio.Event()
    api = make_api(model=gated_model(gate))
    write_minimal_app(workspace_of(api))
    conversation_id = str(uuid4())

    async with http_client(api) as client:
        streaming = asyncio.create_task(post_run_async(client, conversation_id=conversation_id, context_version=0))
        await wait_until_busy(client)
        launched = await client.post("/app/launch", json={})
        assert launched.status_code == 200, launched.text
        assert launched.json()["app_status"] == "healthy"
        health = await client.get("/health")
        assert health.json()["running"] is True
        gate.set()
        streamed = await streaming
        assert streamed.status_code == 200


def test_preview_base_url_override(api: TestClient, launch_port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PREVIEW_BASE_URL", "http://preview.example.com")
    write_minimal_app(workspace_of(api))

    resp = api.post("/app/launch", json={"path": "/app", "label": "Demo"})

    assert resp.status_code == 200
    assert resp.json()["url"] == "http://preview.example.com/app"
    assert resp.json()["label"] == "Demo"


def test_missing_app_is_unavailable(api: TestClient, launch_port: int) -> None:
    resp = api.post("/app/launch", json={})
    assert resp.status_code == 503
    assert api.get("/health").json()["app_status"] == "unhealthy"
