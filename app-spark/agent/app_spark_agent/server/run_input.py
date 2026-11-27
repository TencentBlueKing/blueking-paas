"""The trust boundary for an inbound AG-UI run request.

Everything a client sends is checked here and reduced to the one thing the Runtime is willing
to act on: a single new user turn. The trusted history comes from the Runtime's own context, so
no display history, tool list, or system prompt submitted by the caller ever reaches the model.
"""

import ipaddress
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

from ag_ui.core import (
    PROTOCOL_VERSION,
    DocumentInputContent,
    ImageInputContent,
    InputContent,
    InputContentUrlSource,
    RunAgentInput,
    TextInputContent,
    UserMessage,
)
from fastapi import HTTPException, Request, status
from pydantic_ai import DeferredToolResults
from starlette.types import Message

from app_spark_agent.attachments import ATTACHMENT_URI_SCHEME, IMAGE_MEDIA_TYPES, parse_attachment_id
from app_spark_agent.cap.ask_user import (
    AskUserConflictError,
    AskUserValidationError,
    PendingAskUser,
    build_ask_user_deferred_results,
)
from app_spark_agent.state import AppendLog, ConversationContext

# 用户消息里除了附件引用，也接受外部链接：沙箱本来就能访问外网，模型需要时自己去取。
EXTERNAL_URL_SCHEMES = frozenset({"http", "https"})
ALLOWED_FILE_URL_SCHEMES = EXTERNAL_URL_SCHEMES | {ATTACHMENT_URI_SCHEME}


@dataclass(frozen=True)
class PreparedRun:
    """Validated AG-UI input reduced to one new trusted turn (a user message or question answers)."""

    conversation_id: str
    run_id: str
    context_version: int
    body: bytes
    # None runs the turn on the sandbox's default model.
    model_id: str | None = None
    # False when the control plane says this turn's model cannot read images.
    image_input: bool = True
    # Populated when the caller is answering pending `ask_user_question` tool call(s).
    deferred_tool_results: DeferredToolResults | None = None


def prepare_run(
    body: bytes,
    context: ConversationContext,
    transcript: AppendLog,
) -> PreparedRun:
    """Validate a run and discard caller-submitted display history.

    :param body: Raw AG-UI request document.
    :param context: The Runtime's current trusted context.
    :param transcript: Raw transcript, consulted for replay detection.
    :return: The request reduced to a single trusted user turn.
    :raises HTTPException: 422 for a malformed request, 409 for a conflicting one.
    """
    try:
        run_input = RunAgentInput.model_validate_json(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid AG-UI request.") from exc

    # Only AG-UI 1.0 is spoken here. The adapter keys 1.0-only output (the cancelled outcome of a
    # stopped run) off this declaration, so a client that leaves it out would quietly get a
    # different event stream than the one the stored log and the UI expect.
    if run_input.protocol_version != PROTOCOL_VERSION:
        raise HTTPException(status_code=422, detail=f"protocolVersion must be {PROTOCOL_VERSION!r}.")

    # AG-UI calls a conversation a thread, so `threadId` is the wire name for what this Runtime
    # calls the conversation id everywhere else. The protocol field cannot be renamed, so the
    # translation happens here, once, and the request-shaped error details keep the client's
    # own spelling.
    conversation_id = run_input.thread_id.strip()
    if not conversation_id:
        raise HTTPException(status_code=422, detail="threadId cannot be empty.")
    if context.conversation_id is not None and context.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="threadId does not match the active conversation.",
        )

    try:
        run_id = str(UUID(run_input.run_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="runId must be a UUID.") from exc
    # Asked of the transcript rather than the context: compaction drops old messages, so the
    # context forgets which runs it came from while the append-only log never does.
    if transcript.has_run(run_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="runId has already been committed.",
        )

    forwarded_props = run_input.forwarded_props
    if not isinstance(forwarded_props, dict):
        raise HTTPException(status_code=422, detail="forwardedProps must be an object.")
    typed_forwarded_props = cast(dict[str, object], forwarded_props)
    # camelCase for the same reason as `threadId` above: this key rides inside an AG-UI request
    # document and follows that document's convention. Everything the Runtime itself emits --
    # `/health`, the drain envelopes, the context document -- is snake_case.
    context_version = typed_forwarded_props.get("contextVersion")
    if isinstance(context_version, bool) or not isinstance(context_version, int):
        raise HTTPException(
            status_code=422,
            detail="forwardedProps.contextVersion must be an integer.",
        )
    if context_version != context.context_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Context version mismatch; Runtime is at {context.context_version}.",
        )

    model_id = _read_model_id(typed_forwarded_props)
    image_input = _read_image_input(typed_forwarded_props)

    if "askUserResponses" in typed_forwarded_props:
        deferred_tool_results = _prepare_ask_user_responses(run_input, typed_forwarded_props, context)
        filtered_messages: list[UserMessage] = []
    else:
        deferred_tool_results = None
        filtered_messages = [_extract_user_message(run_input)]

    filtered_input = run_input.model_copy(
        update={
            "thread_id": conversation_id,
            "run_id": run_id,
            "messages": filtered_messages,
            "state": {},
            "tools": [],
            "context": [],
            "forwarded_props": {},
            "resume": None,
        }
    )
    return PreparedRun(
        conversation_id=conversation_id,
        run_id=run_id,
        context_version=context_version,
        body=filtered_input.model_dump_json(by_alias=True).encode(),
        model_id=model_id,
        image_input=image_input,
        deferred_tool_results=deferred_tool_results,
    )


def _prepare_ask_user_responses(
    run_input: RunAgentInput,
    forwarded_props: dict[str, object],
    context: ConversationContext,
) -> DeferredToolResults:
    """Validate `forwardedProps.askUserResponses` and require an empty client message list."""
    if run_input.messages:
        raise HTTPException(
            status_code=422,
            detail="messages must be empty when forwardedProps.askUserResponses is provided.",
        )
    try:
        return build_ask_user_deferred_results(
            forwarded_props["askUserResponses"],
            PendingAskUser(context.messages).tool_calls(),
        )
    except AskUserConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ask_user_conflict", "message": str(exc)},
        ) from exc
    except AskUserValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _extract_user_message(run_input: RunAgentInput) -> UserMessage:
    """Extract and validate the newest `UserMessage` from an inbound run request."""
    user_message = next(
        (message for message in reversed(run_input.messages) if isinstance(message, UserMessage)),
        None,
    )
    if user_message is None:
        raise HTTPException(status_code=422, detail="A user message is required.")
    return user_message.model_copy(update={"content": _check_user_content(user_message.content)})


def _check_user_content(content: str | Sequence[InputContent]) -> str | list[InputContent]:
    """Refuse user content other than text and image or document URLs, and return what is kept."""
    if isinstance(content, str):
        if not content.strip():
            raise HTTPException(status_code=422, detail="The user message cannot be empty.")

        return content

    has_input = False
    checked: list[InputContent] = []
    for part in content:
        if isinstance(part, TextInputContent):
            has_input = has_input or bool(part.text.strip())
            checked.append(part)
            continue

        if not _is_accepted_file(part):
            raise HTTPException(
                status_code=422,
                detail="Only text, app-spark-attachment references and http(s) image or document URLs are accepted.",
            )

        # metadata 由客户端随意填写，其中的 force_download 会让 Agent 替调用方下载它给的地址，一律丢掉。
        checked.append(part.model_copy(update={"metadata": None}))
        has_input = True

    if not has_input:
        raise HTTPException(status_code=422, detail="The user message cannot be empty.")

    return checked


def _is_accepted_file(part: InputContent) -> bool:
    """Return whether a non-text part is an image or document URL this Runtime can handle."""

    # 内联 data 会把字节带进上下文，上游托管的 file 引用模型这边解析不了，只收 URL。
    if not isinstance(part, ImageInputContent | DocumentInputContent) or not isinstance(
        part.source, InputContentUrlSource
    ):
        return False

    url = part.source.value
    is_attachment = parse_attachment_id(url) is not None
    if not is_attachment and not _is_public_web_url(url):
        return False

    # image 段在能看图的模型上会被当图发出（外链由网关去取），所以必须声明为模型能读的图片类型。
    if isinstance(part, ImageInputContent):
        return part.source.mime_type in IMAGE_MEDIA_TYPES

    # 附件引用里的类型是控制面识别出来的：没有类型，模型侧也推断不出来。外链文档只会变成文字，不看类型。
    return bool(part.source.mime_type) or not is_attachment


def _is_public_web_url(url: str) -> bool:
    """Return whether url is an http(s) address on a host that is not obviously internal."""
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError:
        return False

    # 带账号密码的链接会把凭据交给网关；没有主机名的链接让模型调用直接失败。
    if parts.scheme not in EXTERNAL_URL_SCHEMES or not hostname or parts.username or parts.password:
        return False

    # 外链图片由模型网关去取，网关可能在内网里：非公网 IP 一律拒绝。
    try:
        return ipaddress.ip_address(hostname).is_global
    except ValueError:
        pass

    # 其余必须是带顶级域名的域名：挡住 localhost 这类单段主机名，也挡住 2130706433、0x7f.1 这类
    # 会被 HTTP 客户端当成 IP 的写法。域名解析到内网的情况这里查不出来，只能靠网关自己的出网限制。
    labels = hostname.rstrip(".").split(".")
    return len(labels) > 1 and labels[-1].isalpha() and labels[-1] != "localhost"


def _read_model_id(forwarded_props: dict[str, object]) -> str | None:
    """Return the model the turn asked for, or None when it asked for the default."""

    # Only an ID ever crosses here: the model is built from the gateway address and token this
    # Runtime was started with, so a caller can pick which model answers but not where the
    # request goes.
    if "modelId" not in forwarded_props:
        return None

    # A present key must name something. Reading null or "" as "the default" would run the turn
    # on a model the caller did not ask for, without either side noticing.
    model_id = forwarded_props["modelId"]
    if not isinstance(model_id, str) or not model_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="forwardedProps.modelId must be a non-empty string.",
        )

    # Stripped like MODEL_ID, or a padded default ID is neither recognised as the default nor
    # understood by the gateway.
    return model_id.strip()


def _read_image_input(forwarded_props: dict[str, object]) -> bool:
    """Return whether this turn's model may be sent images; absent means it may."""
    image_input = forwarded_props.get("imageInput", True)

    # 只认布尔值：把 "false" 之类读成真值，会把图片发给一个读不了图的模型。
    if not isinstance(image_input, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="forwardedProps.imageInput must be a boolean.",
        )

    return image_input


def request_with_body(request: Request, body: bytes) -> Request:
    """Build a request sharing the original HTTP scope with a filtered body.

    :param request: Request whose scope (headers, client, path) is kept as-is.
    :param body: Body the returned request serves instead of the original one.
    :return: A request the AG-UI adapter can consume the filtered document from.
    """
    body_sent = False

    async def receive() -> Message:
        nonlocal body_sent
        if body_sent:
            return await request.receive()
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(request.scope, receive)
