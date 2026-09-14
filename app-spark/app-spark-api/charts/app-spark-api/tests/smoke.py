# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
#
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
#
# Run with the API image's Python environment; no dependencies are installed by this script.
# ruff: noqa: T201
"""Drive the deployed API through its Service using a disposable database-backed login session.

This seeds test authentication locally; it does not validate an external BlueKing login service.
Re-running after a Helm upgrade verifies conversation recovery and persistent workspace files.
"""

import json
import time
from pathlib import Path

import django
import httpx2

django.setup()

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.token import LoginToken, create_user_from_token
from bkpaas_auth.core.user_info import UserInfo
from bkpaas_auth.middlewares import CookieLoginMiddleware
from django.conf import settings
from django.contrib.auth import login
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest

from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.core.projects.models import Project

PROJECT_ID = "helm-smoke"
BASE_URL = "http://app-spark-api:8000"

# Seed a valid session in the disposable database while keeping the deployed middleware intact.
token = LoginToken(login_token="helm-smoke-token", expires_in=3600)
token.user_info = UserInfo(username="helm-smoke", tenant_id="default")
token.user_info.provider_type = ProviderType.BK
user = create_user_from_token(token)
request = HttpRequest()
request.session = SessionStore()
login(request, user, backend="bkpaas_auth.backends.UniversalAuthBackend")
request.session.update(CookieLoginMiddleware._get_session_data(user, {"bk_token": "helm-smoke-token"}))
request.session.save()
session_key = request.session.session_key
assert session_key is not None
Project.objects.get_or_create(
    id=PROJECT_ID,
    defaults={"name": "Helm Smoke Test", "creator": str(user.pk), "owner": str(user.pk), "tenant_id": "default"},
)

with httpx2.Client(base_url=BASE_URL, timeout=90) as client:
    anonymous = client.get("/api/accounts/userinfo/")
    assert anonymous.status_code == 401, anonymous.text
    client.cookies.set("bk_token", "helm-smoke-token")
    client.cookies.set(settings.SESSION_COOKIE_NAME, session_key)
    authenticated = client.get("/api/accounts/userinfo/")
    assert authenticated.status_code == 200, authenticated.text
    assert authenticated.json()["username"] == "helm-smoke"

    conversation = Conversation.objects.filter(project_id=PROJECT_ID).order_by("number").last()
    if conversation is None:
        created = client.post(f"/api/projects/{PROJECT_ID}/conversations/")
        assert created.status_code == 201, created.text
        number = created.json()["number"]
    else:
        number = conversation.number

    path = f"/api/projects/{PROJECT_ID}/conversations/{number}/"
    before = client.get(path).json()
    workspace = Path(settings.AGENT_RUNTIME_PROVIDER_CONFIG["workspace_root"]) / PROJECT_ID
    note_number = len(list(workspace.glob("fake-agent-note-*.md"))) + 1
    with client.stream("POST", path + "runs/", json={"content": "Write the next test note."}) as response:
        assert response.status_code == 200, response.read()
        assert response.headers["content-type"] == "text/event-stream"
        assert response.headers["x-accel-buffering"] == "no"
        events = [json.loads(line[5:].strip()) for line in response.iter_lines() if line.startswith("data:")]
    event_types = [event["type"] for event in events]
    assert "RUN_STARTED" in event_types, event_types
    assert "RUN_FINISHED" in event_types, event_types
    assert "RUN_ERROR" not in event_types, events
    assert (workspace / f"fake-agent-note-{note_number}.md").is_file()

    # Runtime replication follows the SSE stream. Wait for both the cursor and run state.
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        state = client.get(path).json()
        if (
            not state["running"]
            and not state["replication_pending"]
            and state["context_version"] > before["context_version"]
        ):
            break
        time.sleep(0.1)
    else:
        raise AssertionError(f"State replication did not settle: {state}")
    history = client.get(path + "ui-events/").json()
    assert history["records"], history
    print(
        json.dumps(
            {
                "result": "passed",
                "conversation": number,
                "events": len(events),
                "context_version": state["context_version"],
                "log_seq": state["log_seq"],
                "ui_event_seq": state["ui_event_seq"],
                "workspace_note": f"fake-agent-note-{note_number}.md",
            }
        )
    )
