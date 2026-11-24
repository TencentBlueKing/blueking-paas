"""会话附件：上下文里只存引用，一轮开始前把文件放进工作区，调模型前再换成模型看得懂的内容。

用户消息里只带 app-spark-attachment://<附件 ID>，上下文和回写给控制面的文档都只存引用。

AttachmentMaterializer 在一轮开始前把本轮和上下文里还引用着的附件下载到工作区的
.app-spark/attachments 下。这个目录在平台的 git 排除规则里，不会被提交，也不进发布包；
换了沙箱、工作区从 git 恢复后它是空的，下一轮会按上下文里的引用补齐。

AttachmentResolver 在 wrap_model_request 里复制一份消息，把每个引用换成一行说明（文件名、类型、
大小和工作区里的路径），模型用文件工具按需去读。最近几轮里的图片在能看图的模型上另外直接附上字节。
换过的那份不进历史。不放在 before_model_request：那里改过的消息会写回历史，TranscriptRecorder
还会把它当成一次压缩，立即提交出去。
"""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability, CapabilityOrdering, WrapModelRequestHandler
from pydantic_ai.messages import (
    BinaryContent,
    FileUrl,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextContent,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestContext

from app_spark_agent.replication import AttachmentMeta, AttachmentTooLargeError, ControlPlaneClient, ControlPlaneError

logger = logging.getLogger(__name__)

ATTACHMENT_URI_SCHEME = "app-spark-attachment"
ATTACHMENT_URI_PREFIX = f"{ATTACHMENT_URI_SCHEME}://"

# 能作为图片直接发给模型的类型，与 API 侧的 IMAGE_MIME_TYPES 一致。
IMAGE_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})

# 与 API 的单个附件上限一致。下载时据此截断，防止被指到一个大得离谱的地址。
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024

# 相对工作区。以点开头，模型列目录时不会顺手当成项目代码。
ATTACHMENTS_DIR = Path(".app-spark") / "attachments"

# 本该有这个附件但没拿到：没有控制面、附件不在、token 已吊销、重试后仍失败。这一轮照常继续。
ATTACHMENT_FETCH_FAILED_TEXT = "[Attached file unavailable]"

# 控制面瞬时 5xx 时再试一次前先等一会儿，零间隔重试多半撞上同一个故障。
FETCH_RETRY_DELAY_SECONDS = 0.3

# 落盘的文件名只留常见字符，其余换成下划线：它会出现在给模型的说明和 shell 命令里。
_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\- ]")
MAX_STORED_FILENAME_LENGTH = 100
DEFAULT_STORED_FILENAME = "attachment"


class AttachmentFetchError(Exception):
    """An attachment could not be fetched; retryable is false when it is gone for good."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


type FetchAttachment = Callable[[str], Awaitable[tuple[AttachmentMeta, bytes]]]


@dataclass(frozen=True)
class StoredAttachment:
    """An attachment already in the workspace.

    :param path: Workspace-relative path of the file.
    """

    path: Path
    filename: str
    mime_type: str
    size: int

    def describe(self) -> str:
        """Return the line the model sees in place of the attachment reference."""
        return f"[Attached file: {self.filename} ({self.mime_type}, {self.size} bytes) at {self.path.as_posix()}]"


def parse_attachment_id(url: str) -> str | None:
    """Return the attachment ID an app-spark-attachment:// URL names, or None for any other URL."""
    if not url.startswith(ATTACHMENT_URI_PREFIX):
        return None

    # 只认 UUID：ID 会被拼进请求路径和工作区路径，任何别的东西都可能借机改写路径。
    try:
        return str(UUID(url.removeprefix(ATTACHMENT_URI_PREFIX)))
    except ValueError:
        return None


def build_control_plane_fetcher(client: ControlPlaneClient) -> FetchAttachment:
    """Adapt the control plane client to what AttachmentMaterializer calls, retrying once."""

    async def fetch_once(attachment_id: str) -> tuple[AttachmentMeta, bytes]:
        try:
            meta = await client.get_attachment(attachment_id)
            return meta, await client.download_attachment(meta.source, max_bytes=MAX_ATTACHMENT_BYTES)
        # 超限是内容本身的问题，再下一次还是这么大。
        except AttachmentTooLargeError as exc:
            raise AttachmentFetchError(str(exc), retryable=False) from exc
        except ControlPlaneError as exc:
            # 没收到响应或对方 5xx 可以再试；4xx 是附件不在了、token 已被吊销或签名过期，再试也一样。
            retryable = exc.status_code is None or exc.status_code >= 500
            raise AttachmentFetchError(str(exc), retryable=retryable) from exc

    async def fetch(attachment_id: str) -> tuple[AttachmentMeta, bytes]:
        try:
            return await fetch_once(attachment_id)
        except AttachmentFetchError as exc:
            if not exc.retryable:
                raise

        # 只重试一次：再失败就按不可用处理，不拖住这一轮。重新取元数据，预签名地址可能已经过期。
        await asyncio.sleep(FETCH_RETRY_DELAY_SECONDS)
        return await fetch_once(attachment_id)

    return fetch


class AttachmentMaterializer:
    """Keep the attachments a conversation refers to as files in its workspace.

    :param workspace: The Runtime's workspace root.
    :param fetch: Downloads one attachment by ID; None without a control plane, in which case
        no attachment is ever available.
    """

    def __init__(self, workspace: Path, fetch: FetchAttachment | None) -> None:
        self._workspace = workspace
        self._root = workspace / ATTACHMENTS_DIR
        self._fetch = fetch

    def find(self, attachment_id: str) -> StoredAttachment | None:
        """Return the attachment if it is already in the workspace."""
        meta_path = self._meta_path(attachment_id)

        # 元数据最后写，有它就说明文件已经完整落盘；读坏了也按不在处理，下一轮会重新下载。
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            stored_name = meta["stored_name"]
            stored = StoredAttachment(
                path=ATTACHMENTS_DIR / attachment_id / stored_name,
                filename=meta["filename"],
                mime_type=meta["mime_type"],
                size=int(meta["size"]),
            )
        except OSError, ValueError, KeyError, TypeError:
            return None

        # 元数据在工作区里，模型能改它：文件名必须是我们自己会写出来的样子，不能借它拼出别的路径。
        if not isinstance(stored_name, str) or sanitize_filename(stored_name) != stored_name:
            return None

        file_path = self._resolve_inside(attachment_id, stored_name)
        if file_path is None or not file_path.is_file():
            return None

        return stored

    def read_bytes(self, stored: StoredAttachment) -> bytes:
        """Return a stored attachment's content.

        :raises OSError: If the file is gone, has moved out of its directory, or is over the size limit.
        """
        file_path = self._resolve_inside(stored.path.parent.name, stored.path.name)
        if file_path is None:
            raise OSError(f"{stored.path} is no longer inside its attachment directory")

        # 读回的文件可能已被换掉，套上和下载一样的上限，不把一个大文件整份读进内存发给模型。
        if file_path.stat().st_size > MAX_ATTACHMENT_BYTES:
            raise OSError(f"{stored.path} is larger than {MAX_ATTACHMENT_BYTES} bytes")

        return file_path.read_bytes()

    def _resolve_inside(self, attachment_id: str, name: str) -> Path | None:
        """Return the path of a file in the attachment's directory, or None if a symlink leads elsewhere."""
        expected = self._workspace.resolve() / ATTACHMENTS_DIR / attachment_id / name

        # 解析后必须原样落在预期位置：路径上任何一段是符号链接（例如仓库里提交了一个 .app-spark
        # 链接），读写都会被带到工作区外。
        if (self._workspace / ATTACHMENTS_DIR / attachment_id / name).resolve() != expected:
            return None

        return expected

    async def ensure(self, messages: Sequence[ModelMessage]) -> None:
        """Download every attachment the messages refer to that is not in the workspace yet."""
        missing = sorted(
            {attachment_id for attachment_id in iter_attachment_ids(messages) if self.find(attachment_id) is None}
        )
        if not missing:
            return

        # 没有控制面就无处可取。引用留着，模型看到的是「附件不可用」。
        if self._fetch is None:
            logger.warning("no control plane to fetch attachments %s from", missing)
            return

        # 换沙箱后上下文里的附件会一次缺很多，并发取；单个失败不影响其他附件和这一轮。
        await asyncio.gather(*(self._download(attachment_id) for attachment_id in missing))

    async def _download(self, attachment_id: str) -> None:
        assert self._fetch is not None
        try:
            meta, data = await self._fetch(attachment_id)
        except AttachmentFetchError as exc:
            logger.warning("attachment %s is unavailable: %s", attachment_id, exc)
            return

        stored_name = sanitize_filename(meta.filename)
        file_path = self._resolve_inside(attachment_id, stored_name)
        if file_path is None:
            logger.warning("attachment %s is not written: its path leads out of the workspace", attachment_id)
            return

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(data)
            # 元数据最后写，find 才不会把写了一半的文件当成已就绪。
            self._meta_path(attachment_id).write_text(
                json.dumps(
                    {
                        "stored_name": stored_name,
                        "filename": meta.filename,
                        "mime_type": meta.mime_type,
                        "size": len(data),
                    }
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("attachment %s could not be written to the workspace: %s", attachment_id, exc)

    def _meta_path(self, attachment_id: str) -> Path:
        return self._root / f"{attachment_id}.json"


class AttachmentResolver(AbstractCapability[Any]):
    """Swap attachment references for descriptions, and recent images for bytes, in each model request.

    :param materializer: Where the attachments already are.
    :param recent_turns: How many of the latest user turns have their images sent as bytes.
    :param send_images: False when this turn's model cannot read images, so none are sent.
    """

    def __init__(self, materializer: AttachmentMaterializer, *, recent_turns: int, send_images: bool) -> None:
        self._materializer = materializer
        self._recent_turns = recent_turns if send_images else 0
        self._send_images = send_images

    def get_ordering(self) -> CapabilityOrdering:
        """Run innermost, so no other capability ever sees the swapped-in content."""
        return CapabilityOrdering(position="innermost")

    async def wrap_model_request(
        self,
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        handler: WrapModelRequestHandler,
    ) -> ModelResponse:
        """Hand the model a copy of the request whose file references are resolved."""
        messages = self.resolve_messages(request_context.messages)
        if messages is request_context.messages:
            return await handler(request_context)

        # 新建而不是改传进来的那份：after_model_request 拿到的是原来那份，改了它，
        # TranscriptRecorder 就会把换进来的内容当成压缩结果提交进上下文。
        sent = ModelRequestContext(
            model=request_context.model,
            messages=messages,
            model_settings=request_context.model_settings,
            model_request_parameters=request_context.model_request_parameters,
        )
        sent.model_id = request_context.model_id
        sent.streaming = request_context.streaming
        return await handler(sent)

    def resolve_messages(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """Return a copy with file references resolved and text-only prompts collapsed to strings."""

        if not any(_has_sequence_prompt(message) for message in messages):
            return messages

        recent = self._find_recent_turns(messages)
        resolved: list[ModelMessage] = []
        for index, message in enumerate(messages):
            if not isinstance(message, ModelRequest) or not _has_sequence_prompt(message):
                resolved.append(message)
                continue

            parts = [self._resolve_part(part, send_bytes=index in recent) for part in message.parts]
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

    def _resolve_part(self, part: Any, *, send_bytes: bool) -> Any:
        if not isinstance(part, UserPromptPart) or isinstance(part.content, str):
            return part

        content: list[UserContent] = []
        for item in part.content:
            if isinstance(item, FileUrl):
                content.extend(self._resolve_file_url(item, send_bytes=send_bytes))
            else:
                content.append(item)

        return replace(part, content=_collapse_if_text_only(content))

    def _resolve_file_url(self, item: FileUrl, *, send_bytes: bool) -> list[UserContent]:
        attachment_id = parse_attachment_id(item.url)

        # 外部链接：能看图的模型照常收图片链接，其余换成文字，模型需要时自己去取。
        if attachment_id is None:
            if isinstance(item, ImageUrl) and self._send_images:
                return [item]

            return [f"[Linked file: {item.url}]"]

        stored = self._materializer.find(attachment_id)
        if stored is None:
            return [ATTACHMENT_FETCH_FAILED_TEXT]

        # 说明总在：图片早于最近几轮、或模型看不了图时，模型仍知道文件在哪，需要时能自己读。
        if not (send_bytes and stored.mime_type in IMAGE_MEDIA_TYPES):
            return [stored.describe()]

        # 字节每次从磁盘读，不在内存里留缓存：最近几轮的图有限，读一次本地文件的开销可以忽略。
        try:
            data = self._materializer.read_bytes(stored)
        except OSError as exc:
            logger.warning("attachment %s could not be read from the workspace: %s", attachment_id, exc)
            return [stored.describe()]

        return [stored.describe(), BinaryContent(data=data, media_type=stored.mime_type)]


def sanitize_filename(filename: str) -> str:
    """Return a file name safe to place in the workspace and to show in shell commands."""
    name = _UNSAFE_FILENAME_CHARS.sub("_", Path(filename).name).strip(" .")
    if not name:
        return DEFAULT_STORED_FILENAME

    # 截断时保留扩展名：模型和工具靠它判断怎么打开文件。
    if len(name) > MAX_STORED_FILENAME_LENGTH:
        suffix = Path(name).suffix[:16]
        name = name[: MAX_STORED_FILENAME_LENGTH - len(suffix)] + suffix

    return name


def iter_attachment_ids(messages: Sequence[ModelMessage]) -> Iterator[str]:
    """Yield the ID of every attachment reference in the messages, in order, repeats included."""
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue

        for part in message.parts:
            if not isinstance(part, UserPromptPart) or isinstance(part.content, str):
                continue

            for item in part.content:
                if isinstance(item, FileUrl) and (attachment_id := parse_attachment_id(item.url)) is not None:
                    yield attachment_id


def _collapse_if_text_only(content: list[UserContent]) -> str | list[UserContent]:
    """Join text items into a plain string when no media item remains in the prompt."""

    texts: list[str] = []
    for item in content:
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, TextContent):
            texts.append(item.content)
        else:
            # 含有图片字节或外链图片等多模态块时保留列表，交给能看图的模型按分段结构读取。
            return content

    # OpenAI 兼容层只有看到字符串时才发纯文本 content；保留列表会被发成 type=text 数组，
    # 纯文本模型在网关侧会直接按多模态请求拒绝。
    return "\n".join(text for text in texts if text)


def _has_sequence_prompt(message: ModelMessage) -> bool:
    """Return whether message carries a non-string user prompt that needs resolving or collapsing."""

    if not isinstance(message, ModelRequest):
        return False

    return any(isinstance(part, UserPromptPart) and not isinstance(part.content, str) for part in message.parts)
