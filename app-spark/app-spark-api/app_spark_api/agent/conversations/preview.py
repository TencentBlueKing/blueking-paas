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

"""经由本服务打开某个会话的工作区应用。

浏览器不会被指到沙箱上，而是指回这里，由这里转发。这层间接是预览能被鉴权的全部原因：请求先
过完平台登录和项目归属校验，才够得着模型写的那个进程。于是预览地址本身不是凭据，把它给一个
打不开这个会话的人，他什么也拿不到。

地址也不落库。它是「这个会话」加「本服务对外的地址」的纯函数，存一列只会在服务搬家之后变成
一个没人会去更新的旧值。等 cube 需要一个猜不出来的独立主机名时，那才是该存的东西。

同源的代价分两层，别混在一起看。摘掉转发请求上的 Cookie 和 Authorization，防的是「应用读到平台
凭据」；而「应用以用户身份调平台」是浏览器自己发的同源请求，根本不经过反代，摘首部管不到——那一
层由响应上的 CSP 按路径挡住（见 _build_content_security_policy）。

CSP 是兜底，不是终局。真正干净的做法是给预览换一个独立主机名，那时浏览器的同源策略自己就成立
了，不必靠一串指令去列举该拦什么。换主机名的难点不在这里，在于鉴权：预览请求现在靠平台的登录
Cookie 认人，换了域名那个 Cookie 就不会被带过来，得先有一套签发给预览域的短期票据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

import httpx2
from django.http import StreamingHttpResponse

from app_spark_api.error_codes import error_codes
from app_spark_api.utils.urls import reverse_public

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

    from django.http import HttpRequest

# 反代那条路由的名字。origin 由它反查出来，而不是把路径字面量再抄一遍——把 API 挂到别处时
# 抄出来的那份不会跟着变，前端拿到的就是一个 404。
PREVIEW_APP_URL_NAME = "conversations-preview-app"

# 连不上就快点失败：连接被拒基本等于应用没起来，让 iframe 立刻看见 502 好过一直转圈。
CONNECT_TIMEOUT_SECONDS = 5.0

# 读给得宽一些，预览里的页面自己可能在做长轮询或 SSE。
READ_TIMEOUT_SECONDS = 60.0

# 逐跳首部只描述当前这一段连接，转发出去会让下游按上一段的语义处理，比如把一个 httpx 已经
# 拆过帧的响应继续当成 chunked。
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

# 不交给沙箱里的应用。那是模型写出来的代码，平台的登录 Cookie 和 Bearer 进去就等于交出去了，
# 而预览与控制面同源，浏览器默认就会把 Cookie 带上，所以必须在这里显式摘掉。
# Host 另有原因：它由 httpx 按上游地址自己写。
STRIPPED_REQUEST_HEADERS = frozenset({"cookie", "authorization", "host"})

# 同源的另一面。应用种下的 Cookie 会落在控制面这个域上，一个叫 sessionid 的就能把用户的登录
# 顶掉。应用要存东西请用它自己的存储。
#
# X-Frame-Options 由下面重新写一份，所以上游那份先摘掉：应用自己回一个 DENY 也不该让预览
# 打不开，它并不知道自己正被当成预览展示。
STRIPPED_RESPONSE_HEADERS = frozenset({"set-cookie", "x-frame-options"})

# 预览就是要被 iframe 装起来，而本服务装了 XFrameOptionsMiddleware，X_FRAME_OPTIONS 用的是
# Django 默认的 DENY——不自己写一份，每个预览响应都会被盖上 DENY，iframe 直接白屏。中间件见到
# 已有值就不再覆盖，所以这里写死。
#
# 前端与本服务不同源时 SAMEORIGIN 不够，得改成 frame-ancestors 列出前端的 origin。
FRAME_ANCESTOR_HEADERS = {"x-frame-options": "SAMEORIGIN"}

# 文档类型的响应才需要 CSP。给一张图片带上没坏处，但也没意义，而 CSP 对非文档响应本来就不生效。
DOCUMENT_CONTENT_TYPES = ("text/html", "application/xhtml+xml")

# 和 run 的 SSE 流同一个理由：Nginx 默认要把 body 攒完才交给客户端。读超时放到 60s 是为了让
# 应用自己的长轮询和 SSE 能过，缓冲不关掉那个放宽就白给了。
STREAMING_HEADERS = {"x-accel-buffering": "no"}


def build_preview_origin(request: HttpRequest, *, project_id: str, number: int) -> str:
    """Return the absolute URL a browser opens this conversation's application on.

    :param request: The request being answered; it is what says how this service is addressed.
    :param project_id: Project the conversation belongs to.
    :param number: Conversation number within that Project.
    :return: An absolute URL ending in a slash, so the application's own relative links resolve
        underneath it rather than replacing its last segment.
    """

    # scheme 和 host 都取自这个请求，也就是说信任的是 ALLOWED_HOSTS 和 SECURE_PROXY_SSL_HEADER。
    # TLS 终结在网关而没配后者的部署会签出 http://，前端是 https 时浏览器按 mixed content 拦掉。
    path = reverse_public(
        f"api:{PREVIEW_APP_URL_NAME}",
        kwargs={"project_id": project_id, "number": number, "subpath": "/"},
    )
    return request.build_absolute_uri(path)


async def forward_to_app(
    request: HttpRequest,
    *,
    upstream: str,
    subpath: str,
    preview_root: str,
) -> StreamingHttpResponse:
    """Forward one request to the workspace application and stream its answer back.

    :param request: The already-authorized request. Callers must have resolved the conversation
        first: this does no checking of its own, and the whole point of the indirection is that
        those checks happened.
    :param upstream: Base URL of the application, as the provider reported it.
    :param subpath: Path under that base, starting with a slash.
    :param preview_root: Absolute URL this conversation's application is published under, used
        to bring the application's own redirects back inside the proxy.
    :return: The application's response, streamed rather than buffered.
    :raises APIError: If the application cannot be reached.
    """
    # Django 把 method 标成可空（请求对象还没填好时是 None），但能被路由到这里的请求必然有方法。
    # 断言而不是回落成 GET：真的是 None 时，把一个 POST 当 GET 转出去只会更难查。位置在建 client
    # 之前，免得这条断言自己变成一处泄漏。
    assert request.method is not None

    base = httpx2.URL(upstream)
    url = _build_upstream_url(base, subpath=subpath, query=request.META.get("QUERY_STRING", ""))

    # 不跟随重定向：3xx 是给浏览器的，替它跟下去会把重定向后的内容冒充成原地址的响应。
    client = httpx2.AsyncClient(
        timeout=httpx2.Timeout(CONNECT_TIMEOUT_SECONDS, read=READ_TIMEOUT_SECONDS),
        follow_redirects=False,
    )

    try:
        upstream_request = client.build_request(
            request.method,
            url,
            headers=_collect_request_headers(request),
            content=request.body or None,
        )
        response = await client.send(upstream_request, stream=True)
    except httpx2.HTTPError as exc:
        await client.aclose()
        raise error_codes.PREVIEW_APP_UNREACHABLE from exc
    except BaseException:
        await client.aclose()
        raise

    # 构造响应也放进 try：headers 要过 Django 的校验，应用回一个非 ASCII 的头值就会抛，而那时
    # 生成器还没被迭代过，它的 finally 永远不会跑——连接和 client 就这么漏掉，且可反复触发。
    try:
        return StreamingHttpResponse(
            _stream_body(client, response),
            status=response.status_code,
            reason=response.reason_phrase,
            headers=_collect_response_headers(response, upstream=base, preview_root=preview_root),
        )
    except BaseException:
        await response.aclose()
        await client.aclose()
        raise


def _build_upstream_url(base: httpx2.URL, *, subpath: str, query: str) -> httpx2.URL:
    """Point base at subpath, in a way that cannot move the request to another host.

    :param base: Where the application is, as the provider reported it.
    :param subpath: Path under that base, starting with a slash.
    :param query: The client's raw query string, forwarded as written.
    :return: A URL whose scheme, host, and port are still base's.
    :raises APIError: If subpath is not a path under the preview prefix.
    """
    # 这一条是安全检查，不是参数校验。路由的 path 转换器是 `.+`，所以 `.../preview/app@host/`
    # 也会被匹配，subpath 拿到的是 `@host/`——字符串拼到 base 后面，`@` 前面那截就变成
    # userinfo，host 换成 subpath 里写的那个，请求打去了别处。鉴权只保证「这个人打得开这个
    # 会话」，保证不了「转发目标还是这个会话的应用」。
    if not subpath.startswith("/"):
        raise error_codes.RESOURCE_NOT_FOUND

    # subpath 来自 ASGI 的 scope["path"]，已经被百分号解码过一轮。重新转义再交给 httpx，
    # 否则解码出来的 "?" "#" 会被当成分隔符：`/a%3Fb` 会变成 path=/a、query=b，`/a%23b`
    # 的后半截直接丢掉。safe="/" 只保留路径分隔符本身。
    raw_path = quote(subpath, safe="/")

    # 查询串原样带过去，不解析再拼回来：应用可能依赖重复键或它自己的编码方式。
    if query:
        raw_path = f"{raw_path}?{query}"

    # 只换 path 和 query，authority 由 base 决定，构造上就没有被改掉的余地。
    return base.copy_with(raw_path=raw_path.encode())


async def _stream_body(client: httpx2.AsyncClient, response: httpx2.Response) -> AsyncIterator[bytes]:
    """Yield the application's body as it arrives, then release the connection."""

    # aiter_raw 而不是 aiter_bytes：转发的是上游写在线上的那些字节，解码再重编码既多花一轮
    # CPU，也会让转发出去的 Content-Encoding 和 Content-Length 对不上实际内容。
    try:
        async for chunk in response.aiter_raw():
            yield chunk
    finally:
        await response.aclose()
        await client.aclose()


def _collect_request_headers(request: HttpRequest) -> dict[str, str]:
    """Return the client's headers, minus the ones the application must not see."""
    return {name: value for name, value in request.headers.items() if not _is_stripped(name, STRIPPED_REQUEST_HEADERS)}


def _collect_response_headers(
    response: httpx2.Response,
    *,
    upstream: httpx2.URL,
    preview_root: str,
) -> dict[str, str]:
    """Return the application's headers, minus the ones that must not reach the browser."""

    # 键统一小写，因为下面要按名字查 location 和 content-type。不靠 httpx 恰好也返回小写：那是
    # 它的实现细节，一旦变了这里会安静地什么都查不到——反代于是不改写重定向、也不加 CSP，而两者
    # 都不会让任何请求失败，只会让防护静静地消失。Django 的响应头本身大小写不敏感。
    headers = {
        name.lower(): value
        for name, value in response.headers.items()
        if not _is_stripped(name, STRIPPED_RESPONSE_HEADERS)
    }

    # 3xx 交回浏览器就得让 Location 跟着前缀走，否则第一跳就跳出预览。这不是边角情况：
    # Starlette 默认开 redirect_slashes，`.../preview/app/docs` 会得到一个 307。
    location = headers.get("location")
    if location is not None:
        headers["location"] = _rewrite_location(location, upstream=upstream, preview_root=preview_root)

    headers |= FRAME_ANCESTOR_HEADERS | STREAMING_HEADERS

    if headers.get("content-type", "").startswith(DOCUMENT_CONTENT_TYPES):
        headers["content-security-policy"] = _build_content_security_policy(preview_root)

    return headers


def _build_content_security_policy(preview_root: str) -> str:
    """Return the policy that keeps the application from acting as the user on the platform.

    :param preview_root: Absolute URL the application is published under, ending in a slash.
    :return: A Content-Security-Policy value.
    """

    # 同源的兜底。应用里的 JS 一句 fetch("/api/projects/...") 就带着用户的登录 Cookie 打到平台
    # 接口上了——那是浏览器自己发的请求，根本不经过反代，摘转发那一跳的首部管不到。不管的话等价
    # 于平台 UI 上的持久 XSS，而应用是模型写出来的代码。
    #
    # 按路径限制，而不是把文档丢进 opaque origin（sandbox 不带 allow-same-origin）。后者更彻底，
    # 但会把应用访问自己接口的 XHR 也变成跨源、要应用自己回 CORS 头——预览的用处就是让人看见应用
    # 能跑，不该顺手把它弄坏。CSP 的 source 支持路径前缀，所以只放开预览前缀下面那一段就够。
    return "; ".join(
        (
            # X-Frame-Options 的现代写法，新浏览器优先看这条。
            "frame-ancestors 'self'",
            # fetch / XHR / WebSocket / EventSource 只能打到这个会话自己的前缀下。读平台接口
            # 需要读到响应，而这条正是拦住「读到」的那一层。
            f"connect-src {preview_root}",
            # 表单也拦：POST 到平台接口不需要读响应就能改状态。
            f"form-action {preview_root}",
        )
    )


def _rewrite_location(location: str, *, upstream: httpx2.URL, preview_root: str) -> str:
    """Bring a redirect the application issued back inside the preview prefix.

    :param location: The application's own ``Location`` value.
    :param upstream: Where the application is, so its own address can be recognized.
    :param preview_root: Absolute URL the application is published under, ending in a slash.
    :return: What the browser should be told instead.
    """
    target = httpx2.URL(location)

    # 带 authority 的：只有指向上游自己时才改。指向别处是应用自己的意思，原样交出去。
    if target.host:
        if (target.scheme, target.host, target.port) != (upstream.scheme, upstream.host, upstream.port):
            return location
        return preview_root + target.raw_path.decode().lstrip("/")

    # 根绝对路径会落到控制面自己的路由上，也要拉回前缀下面。
    if location.startswith("/"):
        return preview_root + target.raw_path.decode().lstrip("/")

    # 剩下的是相对地址，浏览器本来就相对当前预览 URL 解析，不必动。
    return location


def _is_stripped(name: str, extra: Iterable[str]) -> bool:
    """Return whether a header is hop-by-hop or on one of the two deny lists."""
    lowered = name.lower()
    return lowered in HOP_BY_HOP_HEADERS or lowered in extra
