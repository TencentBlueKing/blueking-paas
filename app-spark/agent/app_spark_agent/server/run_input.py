"""The trust boundary for an inbound AG-UI run request.

Everything a client sends is checked here and reduced to the one thing the Runtime is willing
to act on: a single new user turn. The trusted history comes from the Runtime's own context, so
no display history, tool list, or system prompt submitted by the caller ever reaches the model.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from ag_ui.core import (
    ImageInputContent,
    InputContent,
    InputContentUrlSource,
    RunAgentInput,
    TextInputContent,
    UserMessage,
)
from fastapi import HTTPException, Request, status
from starlette.types import Message

from app_spark_agent.attachments import IMAGE_MEDIA_TYPES, parse_attachment_id
from app_spark_agent.state import AppendLog, ConversationContext


@dataclass(frozen=True)
class PreparedRun:
    """Validated AG-UI input reduced to one new trusted user turn."""

    conversation_id: str
    run_id: str
    context_version: int
    body: bytes
    # None runs the turn on the sandbox's default model.
    model_id: str | None = None
    # False when the control plane says this turn's model cannot read images.
    image_input: bool = True


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

    user_message = next(
        (message for message in reversed(run_input.messages) if isinstance(message, UserMessage)),
        None,
    )
    if user_message is None:
        raise HTTPException(status_code=422, detail="A user message is required.")

    _check_user_content(user_message.content)

    filtered_input = run_input.model_copy(
        update={
            "thread_id": conversation_id,
            "run_id": run_id,
            "messages": [user_message],
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
    )


def _check_user_content(content: str | Sequence[InputContent]) -> None:
    """Refuse user content other than text and images referenced as app-spark-attachment://."""
    if isinstance(content, str):
        if not content.strip():
            raise HTTPException(status_code=422, detail="The user message cannot be empty.")

        return

    has_input = False
    for part in content:
        if isinstance(part, TextInputContent):
            has_input = has_input or bool(part.text.strip())
            continue

        # 图片只认控制面签发的附件引用。外部 URL 会让 Agent 替调用方去拉任意地址，内联 data
        # 会把字节带进上下文，两者都不放行。
        if (
            isinstance(part, ImageInputContent)
            and isinstance(part.source, InputContentUrlSource)
            and parse_attachment_id(part.source.value) is not None
            and part.source.mime_type in IMAGE_MEDIA_TYPES
        ):
            has_input = True
            continue

        raise HTTPException(
            status_code=422,
            detail="Only text and app-spark-attachment image references are accepted.",
        )

    if not has_input:
        raise HTTPException(status_code=422, detail="The user message cannot be empty.")


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
