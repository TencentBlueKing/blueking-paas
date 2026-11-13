"""会话图片附件：上下文里只存引用，调模型前才换成图片字节。

用户消息里只带 app-spark-attachment://<附件 ID>，上下文和回写给控制面的文档都只存引用。
AttachmentImages 在 wrap_model_request 里复制一份消息、把引用换成字节交给模型，换过的那份不进
历史。不放在 before_model_request：那里改过的消息会写回历史，TranscriptRecorder 还会把它当成
一次压缩，立即把带图片字节的上下文提交出去。
"""

import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace
from typing import Any
from uuid import UUID

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability, CapabilityOrdering, WrapModelRequestHandler
from pydantic_ai.messages import (
    BinaryContent,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestContext

from app_spark_agent.replication import ControlPlaneClient, ControlPlaneError

logger = logging.getLogger(__name__)

ATTACHMENT_URI_SCHEME = "app-spark-attachment"
ATTACHMENT_URI_PREFIX = f"{ATTACHMENT_URI_SCHEME}://"

# 与 API 上传时按文件头识别的类型一致。
IMAGE_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})

# 只写进发给模型的请求副本，不进会话上下文。更早的用户轮不再取字节，用这句告诉模型这里曾经有图。
OMITTED_IMAGE_TEXT = "[Image from an earlier turn omitted]"
# 本该发图但没拿到字节：没有控制面、附件不在、token 已吊销、重试后仍失败，或类型不是这四种图。这一轮照常继续。
UNAVAILABLE_IMAGE_TEXT = "[Image unavailable]"

# 默认只给最近 2 轮、每轮最多 3 张发字节，留一倍余量让下一轮开始时上一轮的图仍然命中。
DEFAULT_CACHE_SIZE = 12


class AttachmentFetchError(Exception):
    """An attachment could not be fetched; retryable is false when it is gone for good."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


type FetchAttachment = Callable[[str], Awaitable[tuple[bytes, str]]]


def parse_attachment_id(url: str) -> str | None:
    """Return the attachment ID an app-spark-attachment:// URL names, or None for any other URL."""
    if not url.startswith(ATTACHMENT_URI_PREFIX):
        return None

    # 只认 UUID：ID 会被拼进请求路径，任何别的东西都可能借机改写路径。
    try:
        return str(UUID(url.removeprefix(ATTACHMENT_URI_PREFIX)))
    except ValueError:
        return None


def build_control_plane_fetcher(client: ControlPlaneClient) -> FetchAttachment:
    """Adapt the control plane client to what AttachmentImages calls."""

    async def fetch(attachment_id: str) -> tuple[bytes, str]:
        try:
            return await client.get_attachment(attachment_id)
        except ControlPlaneError as exc:
            # 没收到响应或对方 5xx 可以再试；4xx 是附件不在了或 token 已被吊销，再试也一样。
            retryable = exc.status_code is None or exc.status_code >= 500
            raise AttachmentFetchError(str(exc), retryable=retryable) from exc

    return fetch


class AttachmentImages(AbstractCapability[Any]):
    """Swap attachment references for image bytes in each model request, without touching history.

    :param fetch: Downloads one attachment by ID; None without a control plane, which turns
        every image into a placeholder.
    :param recent_turns: How many of the latest user turns have their images sent as bytes.
    :param cache_size: How many images are kept in memory between requests.
    """

    def __init__(self, fetch: FetchAttachment | None, *, recent_turns: int, cache_size: int = DEFAULT_CACHE_SIZE):
        self._fetch = fetch
        self._recent_turns = recent_turns
        self._cache_size = cache_size
        self._cache: OrderedDict[str, BinaryContent] = OrderedDict()

    def get_ordering(self) -> CapabilityOrdering:
        """Run innermost, so no other capability ever sees the swapped-in bytes."""
        return CapabilityOrdering(position="innermost")

    async def wrap_model_request(
        self,
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        handler: WrapModelRequestHandler,
    ) -> ModelResponse:
        """Hand the model a copy of the request whose attachment references are resolved."""
        messages = await self.resolve_messages(request_context.messages)
        if messages is request_context.messages:
            return await handler(request_context)

        # 新建而不是改传进来的那份：after_model_request 拿到的是原来那份，改了它，
        # TranscriptRecorder 就会把图片字节当成压缩结果提交进上下文。
        sent = ModelRequestContext(
            model=request_context.model,
            messages=messages,
            model_settings=request_context.model_settings,
            model_request_parameters=request_context.model_request_parameters,
        )
        sent.model_id = request_context.model_id
        sent.streaming = request_context.streaming
        return await handler(sent)

    async def resolve_messages(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """Return a copy with recent images as bytes and older ones as placeholders, or messages itself if none."""
        if not any(_has_attachment(message) for message in messages):
            return messages

        recent = self._find_recent_turns(messages)
        resolved: list[ModelMessage] = []
        for index, message in enumerate(messages):
            if not isinstance(message, ModelRequest) or not _has_attachment(message):
                resolved.append(message)
                continue

            parts = [await self._resolve_part(part, send_bytes=index in recent) for part in message.parts]
            resolved.append(replace(message, parts=parts))

        return resolved

    def _find_recent_turns(self, messages: Sequence[ModelMessage]) -> set[int]:
        if self._recent_turns == 0:
            return set()

        # 按「用户说了一句话」数轮次：第 1 轮带图、后面两轮没图时，第 1 轮的图同样算早了。
        # 工具结果也是 ModelRequest，但不含 UserPromptPart，不算一轮。
        turns = [
            index
            for index, message in enumerate(messages)
            if isinstance(message, ModelRequest) and any(isinstance(part, UserPromptPart) for part in message.parts)
        ]
        return set(turns[-self._recent_turns :])

    async def _resolve_part(self, part: Any, *, send_bytes: bool) -> Any:
        if not isinstance(part, UserPromptPart) or isinstance(part.content, str):
            return part

        content: list[UserContent] = []
        for item in part.content:
            attachment_id = parse_attachment_id(item.url) if isinstance(item, ImageUrl) else None
            if attachment_id is None:
                content.append(item)
            elif send_bytes:
                content.append(await self._load_image(attachment_id))
            else:
                content.append(OMITTED_IMAGE_TEXT)

        return replace(part, content=content)

    async def _load_image(self, attachment_id: str) -> BinaryContent | str:
        if (cached := self._cache.get(attachment_id)) is not None:
            self._cache.move_to_end(attachment_id)
            return cached

        # 取不到图不让这一轮失败：模型看到占位，仍然可以根据文字回答，或者请用户重发。
        try:
            data, media_type = await self._fetch_with_retry(attachment_id)
        except AttachmentFetchError as exc:
            logger.warning("attachment %s is unavailable: %s", attachment_id, exc)
            return UNAVAILABLE_IMAGE_TEXT

        # API 只存这几种类型，对方说是别的就是出了岔子，不把来历不明的字节当图发给模型。
        if media_type not in IMAGE_MEDIA_TYPES:
            logger.warning("attachment %s came back as %r, not an image", attachment_id, media_type)
            return UNAVAILABLE_IMAGE_TEXT

        image = BinaryContent(data=data, media_type=media_type)
        self._cache[attachment_id] = image
        # 内容按 ID 固定不变，缓存不会过时，只需按最近使用淘汰来控制内存。
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

        return image

    async def _fetch_with_retry(self, attachment_id: str) -> tuple[bytes, str]:
        # 本地开发和单测没有控制面，附件无处可取。
        if self._fetch is None:
            raise AttachmentFetchError("no control plane to fetch from", retryable=False)

        # 只重试一次：连不上或对方 5xx 值得再试，再失败就按不可用处理，不拖住这一轮。
        try:
            return await self._fetch(attachment_id)
        except AttachmentFetchError as exc:
            if not exc.retryable:
                raise

        return await self._fetch(attachment_id)


def _has_attachment(message: ModelMessage) -> bool:
    if not isinstance(message, ModelRequest):
        return False

    return any(
        isinstance(item, ImageUrl) and item.url.startswith(ATTACHMENT_URI_PREFIX)
        for part in message.parts
        if isinstance(part, UserPromptPart) and not isinstance(part.content, str)
        for item in part.content
    )
