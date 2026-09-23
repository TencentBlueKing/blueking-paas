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

"""预览地址怎么推出来，以及转发的上游地址怎么被钉死在 provider 给的那台主机上。

上游地址那组是安全用例，所以直接打在构造函数上而不是绕一圈 HTTP：要守的性质是「无论 subpath
写成什么，authority 都不变」，而这正是一个纯函数的性质。请求首部剥离、Location 改写这些经过
整条链路才有意义的行为，在 tests/api/test_conversation_preview.py 里端到端验。
"""

import httpx2
import pytest
from django.test import RequestFactory

from app_spark_api.agent.conversations import preview

UPSTREAM = httpx2.URL("http://127.0.0.1:9001")

PREVIEW_ROOT = "http://testserver/api/projects/p/conversations/3/preview/app/"


@pytest.fixture()
def request_factory() -> RequestFactory:
    return RequestFactory()


# --- 签发地址 --------------------------------------------------------------------------------


def test_the_origin_is_an_absolute_url_under_this_service(request_factory):
    """同源：浏览器打开它先过平台登录，而不是直连沙箱。末尾的斜杠让应用的相对链接落在它下面。"""
    origin = preview.build_preview_origin(
        request_factory.get("/api/projects/spark-demo/conversations/3/preview/"),
        project_id="spark-demo",
        number=3,
    )

    assert origin == "http://testserver/api/projects/spark-demo/conversations/3/preview/app/"


def test_the_origin_keeps_the_public_ingress_prefix(settings, request_factory):
    """服务挂在子路径下时，少了这个前缀前端拿到的就是一个 404。"""
    settings.FORCE_SCRIPT_NAME = "/api-svc"

    origin = preview.build_preview_origin(
        request_factory.get("/api/projects/spark-demo/conversations/3/preview/"),
        project_id="spark-demo",
        number=3,
    )

    assert origin == "http://testserver/api-svc/api/projects/spark-demo/conversations/3/preview/app/"


def test_the_origin_does_not_depend_on_which_path_asked_for_it(request_factory):
    """它是（会话, 本服务地址）的函数。不是的话就不能在会话刚建好、还没人请求过时也签得出来。"""
    from_resource = preview.build_preview_origin(
        request_factory.get("/api/projects/p/conversations/3/preview/"), project_id="p", number=3
    )
    from_elsewhere = preview.build_preview_origin(request_factory.get("/whatever/"), project_id="p", number=3)

    assert from_resource == from_elsewhere


# --- 上游地址钉死在 provider 给的主机上 --------------------------------------------------------


@pytest.mark.parametrize(
    "subpath",
    [
        pytest.param("/", id="root"),
        pytest.param("/page", id="a-page"),
        pytest.param("/a/b/c", id="nested"),
        pytest.param("/%40not-a-host/", id="an-encoded-at-sign"),
        pytest.param("/a?b", id="a-decoded-question-mark"),
        pytest.param("/a#b", id="a-decoded-hash"),
        pytest.param("/..%2F..%2Fetc", id="parent-segments"),
        pytest.param("/中文", id="non-ascii"),
    ],
)
def test_no_subpath_can_move_the_request_to_another_host(subpath):
    """鉴权只保证「这个人打得开这个会话」，保证不了「转发目标还是这个会话的应用」。"""
    url = preview._build_upstream_url(UPSTREAM, subpath=subpath, query="")

    assert (url.scheme, url.host, url.port) == ("http", "127.0.0.1", 9001)


@pytest.mark.parametrize(
    "subpath",
    [
        pytest.param("@evil.example/", id="userinfo-trick"),
        pytest.param("@127.0.0.1:8090/health", id="userinfo-trick-onto-the-agent"),
        pytest.param("not-a-path", id="no-leading-slash"),
    ],
)
def test_a_subpath_that_is_not_a_path_is_refused(subpath):
    """路由的 path 转换器是 `.+`，所以 `.../preview/app@别的主机/` 也会匹配上。

    拼到上游地址后面，`@` 前面那截就变成 userinfo，host 换成 subpath 里写的那个。
    """
    with pytest.raises(Exception, match="Resource not found"):
        preview._build_upstream_url(UPSTREAM, subpath=subpath, query="")


def test_a_decoded_separator_in_the_path_is_escaped_again():
    """ASGI 给的 path 已经解码过一轮，`%3F` 变成 `?` 会被当成查询分隔符，后半截就丢了。"""
    url = preview._build_upstream_url(UPSTREAM, subpath="/a?b", query="")

    assert url.raw_path == b"/a%3Fb"


def test_the_query_string_is_forwarded_as_written():
    """应用可能依赖重复键或它自己的编码方式，解析再拼回来会改掉它看到的东西。"""
    url = preview._build_upstream_url(UPSTREAM, subpath="/search", query="x=1&x=2&raw=a%20b")

    assert url.raw_path == b"/search?x=1&x=2&raw=a%20b"


# --- 应用自己发的重定向 ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        # Starlette 默认开 redirect_slashes，这两种形态都很常见。
        pytest.param("/docs/", f"{PREVIEW_ROOT}docs/", id="root-absolute"),
        pytest.param("http://127.0.0.1:9001/docs/", f"{PREVIEW_ROOT}docs/", id="upstream-absolute"),
        pytest.param("http://127.0.0.1:9001/x?a=1", f"{PREVIEW_ROOT}x?a=1", id="upstream-with-query"),
        # 不含 .. 的相对地址，按当前页解析后仍在前缀下。
        pytest.param("next/", f"{PREVIEW_ROOT}next/", id="relative-stays-under-the-prefix"),
        # 指向别处是应用自己的意思。
        pytest.param("https://other.example/x", "https://other.example/x", id="another-host-is-left-alone"),
    ],
)
def test_a_redirect_is_brought_back_inside_the_preview_prefix(location, expected):
    """不改写的话 iframe 第一跳就跳出预览：要么落到控制面自己的路由上，要么去连用户的回环地址。"""
    rewritten = preview._rewrite_location(
        location, upstream=UPSTREAM, preview_root=PREVIEW_ROOT, current_url=PREVIEW_ROOT
    )

    assert rewritten == expected


@pytest.mark.parametrize(
    "location",
    [
        pytest.param("/../../../etc/admin", id="root-absolute-climbs-out"),
        pytest.param("http://127.0.0.1:9001/../../api/accounts/", id="upstream-absolute-climbs-out"),
        pytest.param("../../etc/admin", id="relative-climbs-out"),
    ],
)
def test_a_redirect_cannot_climb_out_of_the_preview_prefix(location):
    """`..` 不折叠的话，浏览器归一化之后会落到控制面自己的路由上，还带着用户的登录态。"""
    current = f"{PREVIEW_ROOT}deep/page"
    rewritten = preview._rewrite_location(location, upstream=UPSTREAM, preview_root=PREVIEW_ROOT, current_url=current)

    assert rewritten.startswith(PREVIEW_ROOT)


# --- 告诉应用它其实被挂在哪 ------------------------------------------------------------------


def test_the_application_is_told_where_the_browser_actually_reached_it(request_factory):
    """不补这组，应用看到的客户端是本服务、协议是 http、主机是沙箱内网地址。

    前缀那条尤其关键：沙箱按设计不知道预览地址，应用于是会把自己的链接拼成 `/static/x.css`，
    落到控制面的路由上 404。读 X-Forwarded-Prefix 的框架能自己把它拼对。
    """
    request = request_factory.get("/api/projects/p/conversations/3/preview/app/page", REMOTE_ADDR="10.0.0.7")

    headers = preview._collect_request_headers(request, preview_root=PREVIEW_ROOT)

    assert headers["x-forwarded-proto"] == "http"
    assert headers["x-forwarded-host"] == "testserver"
    assert headers["x-forwarded-prefix"] == "/api/projects/p/conversations/3/preview/app"
    assert headers["x-forwarded-for"] == "10.0.0.7"


def test_an_existing_forwarded_chain_is_appended_to_not_replaced(request_factory):
    """本服务前面还有接入层，它写下的那一段也是链路的一部分。"""
    request = request_factory.get("/whatever/", REMOTE_ADDR="10.0.0.7", HTTP_X_FORWARDED_FOR="203.0.113.9")

    headers = preview._collect_request_headers(request, preview_root=PREVIEW_ROOT)

    assert headers["x-forwarded-for"] == "203.0.113.9, 10.0.0.7"


def test_a_client_supplied_forwarded_header_cannot_reach_the_application_as_written(request_factory):
    """整组重写，不让应用读到半新半旧的一份——它无从分辨哪条是接入层写的、哪条是浏览器编的。"""
    request = request_factory.get(
        "/whatever/",
        REMOTE_ADDR="10.0.0.7",
        HTTP_X_FORWARDED_HOST="evil.example",
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_X_FORWARDED_PREFIX="/admin",
    )

    headers = preview._collect_request_headers(request, preview_root=PREVIEW_ROOT)

    forwarded = {name: value for name, value in headers.items() if name.lower().startswith("x-forwarded-")}
    assert forwarded == {
        "x-forwarded-for": "10.0.0.7",
        "x-forwarded-proto": "http",
        "x-forwarded-host": "testserver",
        "x-forwarded-prefix": "/api/projects/p/conversations/3/preview/app",
    }


# --- 同源的兜底 ------------------------------------------------------------------------------


def test_the_policy_confines_the_application_to_its_own_prefix():
    """应用里的 JS 一句 fetch("/api/...") 就带着用户的登录 Cookie 打到平台接口上了。

    那是浏览器自己发的同源请求，根本不经过反代，摘请求首部管不到。CSP 的 source 支持路径前缀，
    所以能只放开这个会话自己那一段：应用访问自己接口照常，打平台接口的被拦。
    """
    policy = preview._build_content_security_policy(PREVIEW_ROOT)

    directives = dict(part.strip().split(" ", 1) for part in policy.split(";"))
    assert directives["connect-src"] == PREVIEW_ROOT
    assert directives["form-action"] == PREVIEW_ROOT
    assert directives["frame-ancestors"] == "'self'"
    # 没选 opaque origin 那条路：它会把应用访问自己接口的 XHR 也变成跨源。
    assert "sandbox" not in policy
