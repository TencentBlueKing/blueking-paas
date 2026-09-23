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

"""打开一个会话的工作区应用：地址从哪儿来，转到哪儿去，谁打不开，应用又看得见什么。

工作区应用换成一个会记下收到的请求的本地 HTTP 服务——要验的不是 agent 怎么跑起来的（那是
``test_conversations.py`` 的事），而是控制面把请求转给了谁、让浏览器和应用各自看见了什么。
Runtime 那一侧直接假掉 ``health()``：``/health`` 的解析在 tests/agent/runtime/test_entities.py 里，
这边只关心那个状态有没有走到响应上。
"""

from __future__ import annotations

import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

import attrs
import pytest

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.runtime import (
    AgentRuntimeClient,
    AgentRuntimeHandle,
    AgentUnavailableError,
    RuntimeHealth,
    get_agent_runtime_provider,
)
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from tests.api.support import CONVERSATIONS_URL, configure_local_provider, create_reachable_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytestmark = pytest.mark.django_db(transaction=True)

# 一串只有工作区应用会写出来的字节。只在真的起了应用的用例里断言它——没起应用时它恒不出现，
# 那样的断言什么也没证明。
APP_MARKER = "only-the-workspace-application-writes-this"

HTML = {"Content-Type": "text/html; charset=utf-8"}

# 「没给 dev_server_status」和「给了 None」是两回事：前者表示压根没有 Runtime，后者表示有但读不出来。
_NO_RUNTIME = object()

# 除 dev_server_status 之外的字段这边一概不关心，用一份固定的垫底。
HEALTH = RuntimeHealth(
    model="fake:write-file",
    conversation_id=None,
    context_version=0,
    log_seq=0,
    ui_event_seq=0,
    running=False,
)


@dataclass
class Received:
    """One request the fake application saw, as it saw it."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@dataclass
class FakeApp:
    """A stand-in workspace application: what it answers, and what it was asked."""

    marker: str = APP_MARKER
    extra_headers: dict[str, str] = field(default_factory=dict)
    status: int = HTTPStatus.OK
    received: list[Received] = field(default_factory=list)


class _AppHandler(BaseHTTPRequestHandler):
    """Record the request, then answer with whatever the FakeApp was configured to say."""

    def _handle(self) -> None:
        app: FakeApp = self.server.app  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length") or 0)
        app.received.append(
            Received(
                method=self.command,
                path=self.path,
                headers={name.lower(): value for name, value in self.headers.items()},
                body=self.rfile.read(length) if length else b"",
            )
        )

        body = f"{app.marker}{self.path}".encode()
        self.send_response(app.status)
        for name, value in app.extra_headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _handle
    do_POST = _handle

    def log_message(self, *_args: object) -> None:
        """Keep the test output free of one access log line per request."""


@contextmanager
def serving_app(app: FakeApp) -> Iterator[str]:
    """Run the fake application on a throwaway port, and yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _AppHandler)
    server.app = app  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def find_unused_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def collect_body(response) -> bytes:
    """Read a proxied response whole; the async test client hands back an async iterator."""
    return b"".join([chunk async for chunk in response.streaming_content])


def build_preview_url(number: int) -> str:
    return f"{CONVERSATIONS_URL}{number}/preview/"


def build_app_url(number: int, subpath: str = "/") -> str:
    return f"{CONVERSATIONS_URL}{number}/preview/app{subpath}"


@pytest.fixture(autouse=True)
def runtime_provider(settings, tmp_path: Path) -> None:
    """Nothing here ever spawns a Runtime; the provider only has to exist."""
    configure_local_provider(settings, tmp_path)


@pytest.fixture
def project(bk_user) -> Project:
    return create_reachable_project(bk_user)


@pytest.fixture
def conversation(project, bk_user) -> Conversation:
    return Conversation.objects.create_for_project(project, owner=bk_user.pk)


@pytest.fixture
def stage(monkeypatch):
    """Put an application, and a Runtime's verdict on it, behind one conversation.

    A callable rather than a value: the isolation rule needs two conversations staged at once,
    which is the only way to show that neither reaches the other's application.

    ``dev_server_status`` has three shapes here, matching the three the service has to tell
    apart: not passed means no Runtime at all, ``None`` means a Runtime that cannot be read, and
    a string is whatever a live one reported.
    """
    apps: dict[str, str] = {}
    statuses: dict[str, str | None] = {}

    async def fake_preview_upstream(conversation_id: str) -> str | None:
        return apps.get(conversation_id)

    async def fake_peek(conversation_id: str) -> AgentRuntimeHandle | None:
        if conversation_id not in statuses:
            return None
        return AgentRuntimeHandle(
            conversation_id=conversation_id,
            base_url="http://127.0.0.1:1",
            runtime_token="runtime-token",
        )

    async def fake_health(self: AgentRuntimeClient) -> RuntimeHealth:
        status = statuses[self.handle.conversation_id]
        if status is None:
            raise AgentUnavailableError("the Runtime could not be reached")
        return attrs.evolve(HEALTH, dev_server_status=status)

    provider = get_agent_runtime_provider()
    monkeypatch.setattr(provider, "preview_upstream", fake_preview_upstream)
    monkeypatch.setattr(provider, "peek", fake_peek)
    monkeypatch.setattr(AgentRuntimeClient, "health", fake_health)

    def attach(conversation: Conversation, *, app: str | None = None, dev_server_status=_NO_RUNTIME) -> None:
        if app is not None:
            apps[str(conversation.id)] = app
        if dev_server_status is not _NO_RUNTIME:
            statuses[str(conversation.id)] = dev_server_status

    return attach


# --- 地址 ------------------------------------------------------------------------------------


async def test_a_conversation_can_be_opened_before_anything_has_been_run(aapi_client, conversation):
    """地址在会话建好那一刻就有。它不是某个 Runtime 报上来的东西，也就不必等谁先跑起来。"""
    body = (await aapi_client.get(build_preview_url(conversation.number))).json()

    assert body["origin"].endswith(f"/conversations/{conversation.number}/preview/app/")
    # 不是回环地址：那是「浏览器和后端同机」时才碰巧对的答案。
    assert "127.0.0.1" not in body["origin"]
    # 地址有了但没东西可看，这两件事是分开的。
    assert body["dev_server_status"] is None


@pytest.mark.parametrize(
    ("staged", "expected"),
    [
        pytest.param({"dev_server_status": "ready"}, "ready", id="a-live-runtime-reports"),
        pytest.param({"dev_server_status": None}, None, id="an-unreadable-runtime-reports-nothing"),
        pytest.param({}, None, id="no-runtime-at-all"),
    ],
)
async def test_the_address_holds_while_only_the_status_moves(aapi_client, conversation, stage, staged, expected):
    """探针失败只该改变状态。让接口 5xx、或者把地址抹掉，都会连着毁掉一个仍然有效的 origin。"""
    stage(conversation, **staged)

    response = await aapi_client.get(build_preview_url(conversation.number))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["origin"].endswith(f"/conversations/{conversation.number}/preview/app/")
    assert response.json()["dev_server_status"] == expected


# --- 反代 ------------------------------------------------------------------------------------


async def test_the_path_and_query_reach_the_application_verbatim(aapi_client, conversation, stage):
    app = FakeApp()
    with serving_app(app) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(build_app_url(conversation.number, "/page?x=1&x=2"))

        assert response.status_code == HTTPStatus.OK
        assert (await collect_body(response)).decode() == f"{APP_MARKER}/page?x=1&x=2"

    # 查询串原样过去：应用可能依赖重复键或它自己的编码方式。
    assert app.received[0].path == "/page?x=1&x=2"


async def test_a_write_request_reaches_the_application_with_its_body(aapi_client, conversation, stage):
    """路由声明接 POST/PUT/PATCH/DELETE，方法和正文就都得原样过去。"""
    app = FakeApp()
    with serving_app(app) as upstream:
        stage(conversation, app=upstream)

        await collect_body(
            await aapi_client.post(
                build_app_url(conversation.number, "/submit"),
                data=b'{"a":1}',
                content_type="application/json",
            )
        )

    assert (app.received[0].method, app.received[0].body) == ("POST", b'{"a":1}')


@pytest.mark.parametrize(
    "upstream_headers",
    [
        pytest.param({}, id="an-application-that-says-nothing"),
        # 应用自己回 DENY 也不该让预览打不开，它并不知道自己正被当成预览展示。
        pytest.param({"X-Frame-Options": "DENY"}, id="an-application-that-forbids-framing"),
    ],
)
async def test_the_response_can_be_put_in_an_iframe_and_is_not_buffered(
    aapi_client, conversation, stage, upstream_headers
):
    """本服务装了 XFrameOptionsMiddleware 且用默认的 DENY——被盖上预览就是白屏。

    X-Accel-Buffering 同理是必需的：读超时放到 60s 是为了让应用的 SSE 过得去，Nginx 的缓冲不关
    掉那个放宽就白给了。
    """
    with serving_app(FakeApp(extra_headers=upstream_headers)) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(build_app_url(conversation.number))
        await collect_body(response)

    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_a_page_the_model_wrote_cannot_call_the_platform_as_the_user(aapi_client, conversation, stage):
    """同源的兜底：应用里的 JS 自己发的同源 fetch 不经过反代，摘请求首部管不到它。"""
    with serving_app(FakeApp(extra_headers=HTML)) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(build_app_url(conversation.number))
        await collect_body(response)

    root = f"http://testserver{build_app_url(conversation.number)}"
    assert f"connect-src {root}" in response.headers["Content-Security-Policy"]
    assert f"form-action {root}" in response.headers["Content-Security-Policy"]


async def test_a_non_document_response_carries_no_policy(aapi_client, conversation, stage):
    """声明了非文档类型的响应不注入 CSP。没声明类型的不行：浏览器会嗅探成 HTML。"""
    with serving_app(FakeApp(extra_headers={"Content-Type": "image/png"})) as upstream:
        stage(conversation, app=upstream)

        image = await aapi_client.get(build_app_url(conversation.number, "/logo.png"))
        await collect_body(image)

    assert "Content-Security-Policy" not in image.headers
    assert image.headers["X-Content-Type-Options"] == "nosniff"

    with serving_app(FakeApp()) as upstream:
        stage(conversation, app=upstream)

        untyped = await aapi_client.get(build_app_url(conversation.number, "/page"))
        await collect_body(untyped)

    assert "Content-Security-Policy" in untyped.headers


async def test_credentials_cross_neither_direction(aapi_client, conversation, stage):
    """应用是模型写的代码。预览与控制面同源，两个方向的 Cookie 都得拦。"""
    leaky = FakeApp(extra_headers={"Set-Cookie": "sessionid=hijacked; Path=/"})
    with serving_app(leaky) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(
            build_app_url(conversation.number),
            headers={"Authorization": "Bearer platform-token"},
        )
        await collect_body(response)

    # 会话靠 Cookie 认，而请求确实带着它进来了——否则下面两条什么也没证明。
    assert aapi_client.cookies
    assert "cookie" not in leaky.received[0].headers
    assert "authorization" not in leaky.received[0].headers
    # 反方向：一个叫 sessionid 的 Cookie 就能把用户顶下线。
    assert "Set-Cookie" not in response.headers


async def test_a_redirect_the_application_issues_stays_inside_the_preview(aapi_client, conversation, stage):
    """不改写的话 iframe 第一跳就落到控制面自己的路由上。Starlette 默认开 redirect_slashes。"""
    redirecting = FakeApp(status=HTTPStatus.TEMPORARY_REDIRECT, extra_headers={"Location": "/docs/"})
    with serving_app(redirecting) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(build_app_url(conversation.number))
        await collect_body(response)

    assert response.headers["Location"].endswith(f"/conversations/{conversation.number}/preview/app/docs/")


async def test_two_conversations_never_reach_each_others_application(
    aapi_client, project, bk_user, conversation, stage
):
    """一台机器上两个会话各自的应用。转到哪儿只由路径里的会话决定，请求里没有别的开关。"""
    other = await services.create_conversation(project, owner=bk_user.pk)

    with serving_app(FakeApp(marker="first-app")) as first, serving_app(FakeApp(marker="second-app")) as second:
        stage(conversation, app=first)
        stage(other, app=second)

        first_body = await collect_body(await aapi_client.get(build_app_url(conversation.number)))
        second_body = await collect_body(await aapi_client.get(build_app_url(other.number)))

    assert (first_body, second_body) == (b"first-app/", b"second-app/")


@pytest.mark.parametrize(
    "subpath",
    [
        pytest.param("@127.0.0.1:1/", id="userinfo-trick"),
        pytest.param("@evil.example/", id="userinfo-trick-onto-another-host"),
    ],
)
async def test_the_proxy_target_cannot_be_moved_by_the_path(aapi_client, conversation, stage, subpath):
    """路由的 path 转换器是 `.+`，`.../preview/app@别的主机/` 也会匹配上。

    拼到上游地址后面，`@` 前面那截会变成 userinfo，host 换成路径里写的那个——一条被鉴权路径
    送出去的 SSRF。
    """
    app = FakeApp()
    with serving_app(app) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(build_app_url(conversation.number, subpath))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert app.received == []


async def test_a_conversation_without_a_runtime_has_nothing_to_open(aapi_client, conversation):
    """跑一轮对话就有 Runtime 了，用户自己能解决——所以和下面那条要能分开。"""
    response = await aapi_client.get(build_app_url(conversation.number))

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


async def test_an_application_that_is_not_listening_is_a_bad_gateway(aapi_client, conversation, stage):
    """Runtime 在，但模型还没把应用拉起来。用户能做的不一样，所以状态码也不一样。"""
    stage(conversation, app=f"http://127.0.0.1:{find_unused_port()}")

    response = await aapi_client.get(build_app_url(conversation.number))

    assert response.status_code == HTTPStatus.BAD_GATEWAY


# --- 谁打不开 --------------------------------------------------------------------------------


@pytest.mark.parametrize("url_of", [build_preview_url, build_app_url])
async def test_an_anonymous_caller_reaches_neither_the_address_nor_the_application(
    aanonymous_api_client, conversation, stage, url_of
):
    """URL 不是凭据。预览和控制面同源，正是为了让这道检查挡在应用前面。"""
    with serving_app(FakeApp()) as upstream:
        stage(conversation, app=upstream)

        response = await aanonymous_api_client.get(url_of(conversation.number))

    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}
    assert APP_MARKER not in response.content.decode()


async def test_a_caller_from_another_project_cannot_open_the_application(aapi_client, conversation, stage, bk_user):
    """会话编号只在 Project 内唯一，所以归属必须复查，不能信路径里那个 project_id。"""
    await Project.objects.acreate(
        id="someone-elses",
        name="Someone Else",
        creator=bk_user,
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )
    with serving_app(FakeApp()) as upstream:
        stage(conversation, app=upstream)

        response = await aapi_client.get(
            f"/api/projects/someone-elses/conversations/{conversation.number}/preview/app/"
        )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert APP_MARKER not in response.content.decode()
