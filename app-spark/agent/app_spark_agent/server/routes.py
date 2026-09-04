"""HTTP views: health, drain, context, and the AG-UI run."""

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic_ai.run import AgentRunResult
from pydantic_ai.ui.ag_ui import AGUIAdapter
from starlette.responses import JSONResponse, Response

# Imported at runtime, not under TYPE_CHECKING: this module's annotations are read by tooling
# and by the framework, and a name that only exists for a type checker turns any such read into
# a NameError. ``starlette.types`` is a module of aliases, so importing it costs nothing.
from starlette.types import Receive, Scope, Send

from app_spark_agent import VERSION, settings

# Imported under a different name: `log` already means "append-only channel" in this module.
from app_spark_agent.observability import log as logger
from app_spark_agent.recorder import TranscriptRecorder, record_messages
from app_spark_agent.server.run_input import prepare_run, request_with_body
from app_spark_agent.server.runtime import ConversationRuntime, RunLease, RuntimeBusyError
from app_spark_agent.state import (
    AppendLog,
    AppendLogError,
    Channel,
    ConversationContext,
    ConversationStateConflict,
    ConversationStateError,
    CursorStateError,
)
from app_spark_agent.ui_events import record_ui_events

router = APIRouter()

# Placeholder until the app manager lands and this becomes an enum of real app states.
APP_STATUS_NOT_STARTED = "not_started"
SSE_RESPONSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class _HoldStreamingResponse(StreamingResponse):
    """SSE response that holds a lease and still uses Starlette disconnect handling.

    The parent cancels the generator on ``http.disconnect``; ``generate``'s
    ``finally`` releases a lease that was entered. This path covers handshake
    failure when the generator never started.
    """

    def __init__(self, content: Any, lease: RunLease, **kwargs: Any) -> None:
        super().__init__(content, **kwargs)
        self._lease = lease

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._lease.release_if_never_started()


def attach_runtime(app: FastAPI, runtime: ConversationRuntime) -> None:
    """Give ``app`` the conversation its views will serve."""
    app.state.conversation_runtime = runtime


def get_runtime(request: Request) -> ConversationRuntime:
    """Return the conversation this process serves."""
    # `Request.app` is typed as `Any` and `State` accepts arbitrary attributes, so the type has
    # to be restored by hand -- this is the one place that does it.
    return cast(ConversationRuntime, request.app.state.conversation_runtime)


RuntimeDep = Annotated[ConversationRuntime, Depends(get_runtime)]


def require_bearer(request: Request) -> None:
    """Reject a missing or incorrect Bearer token."""
    if not settings.matches_bearer(request.headers.get("authorization")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.get("/health", dependencies=[Depends(require_bearer)])
async def health(runtime: RuntimeDep) -> dict[str, object]:
    """Report the conversation's identity, the cursor of every stream, and replication lag.

    The ``pushed_*`` cursors are what tells the control plane whether this Runtime is safe to
    discard. They read ``0`` for a Runtime with no control plane configured, where the question
    does not apply.

    ``replication_pending`` is the same question already answered: ``running`` going false only
    means no run holds the guard, *not* that the turn reached the control plane, because a flush
    that times out still hands the guard back. A caller waiting for a turn to be durable
    elsewhere has to see both flags down.
    """
    context = runtime.context_store.context
    replicator = runtime.replicator
    return {
        "version": VERSION,
        "model_ready": settings.is_model_ready(),
        "running": runtime.run_guard.busy,
        "app_status": APP_STATUS_NOT_STARTED,
        "model": settings.MODEL,
        "conversation_id": context.conversation_id,
        "context_version": context.context_version,
        "log_seq": runtime.transcript.last_seq,
        "ui_event_seq": runtime.ui_events.last_seq,
        "replicating": replicator is not None,
        "replication_pending": replicator is not None and bool(replicator.outstanding()),
        "pushed_log_seq": runtime.cursors.channel(Channel.MESSAGE).pushed_seq,
        "pushed_ui_event_seq": runtime.cursors.channel(Channel.UI_EVENT).pushed_seq,
        "pushed_context_version": runtime.cursors.pushed_context_version,
    }


@router.get("/log", dependencies=[Depends(require_bearer)])
async def read_log(
    runtime: RuntimeDep,
    since: int = Query(default=0),
    limit: int = Query(default=settings.DEFAULT_DRAIN_LIMIT),
) -> JSONResponse:
    """Return one page of the raw model transcript."""
    return _drain(runtime.transcript, since, limit)


@router.get("/ui-events", dependencies=[Depends(require_bearer)])
async def read_ui_events(
    runtime: RuntimeDep,
    since: int = Query(default=0),
    limit: int = Query(default=settings.DEFAULT_DRAIN_LIMIT),
) -> JSONResponse:
    """Return one page of the AG-UI event history."""
    return _drain(runtime.ui_events, since, limit)


@router.get("/context", dependencies=[Depends(require_bearer)])
async def read_context(runtime: RuntimeDep) -> JSONResponse:
    """Export the context the next run will be given, tagged with its version."""
    context = runtime.context_store.context
    return JSONResponse(
        context.as_payload(),
        headers={"ETag": str(context.context_version)},
    )


@router.put("/context", dependencies=[Depends(require_bearer)])
async def restore_context(
    request: Request,
    runtime: RuntimeDep,
    log_seq: int = Query(default=0, ge=0),
    ui_event_seq: int = Query(default=0, ge=0),
) -> JSONResponse:
    """Inject a cold context into an empty Runtime, and tell it where its history stands.

    The two cursors ride as query parameters rather than inside the body, because the body has
    to stay byte-for-byte the document ``GET /context`` produced -- that is what makes a
    conversation movable by copying one file. They are the sequence numbers the control plane
    already holds for this conversation; this Runtime's channels continue after them instead of
    restarting at 1 and colliding.

    :param log_seq: Sequence number the raw transcript should continue from.
    :param ui_event_seq: Sequence number the AG-UI event history should continue from.
    """
    async with runtime.run_guard.exclusive():
        current = runtime.context_store.context.context_version
        expected = request.headers.get("if-match")
        if expected is not None and expected != str(current):
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail=f"contextVersion does not match; Runtime is at {current}.",
            )
        try:
            raw = await request.json()
            context = ConversationContext.from_payload(raw)
            restored = await runtime.restore(
                context,
                log_seq=log_seq,
                ui_event_seq=ui_event_seq,
            )
        except (ConversationStateConflict, AppendLogError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ConversationStateError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except CursorStateError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON context payload.") from exc
        return JSONResponse(
            restored.as_payload(),
            headers={"ETag": str(restored.context_version)},
        )


@router.post("/runs", dependencies=[Depends(require_bearer)])
async def run(request: Request, runtime: RuntimeDep) -> Response:
    """Run one conversation turn and stream it back as AG-UI events."""
    if not settings.is_model_ready():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not ready")
    lease = await runtime.run_guard.try_acquire()
    if lease is None:
        raise RuntimeBusyError("An Agent run is already in progress.")

    try:
        response, run_id = await _start_run(runtime, request)
    except Exception:
        lease.release()
        raise
    return _hold_run_stream(response, lease, runtime=runtime, run_id=run_id)


async def _start_run(runtime: ConversationRuntime, request: Request) -> tuple[Response, str]:
    """Validate one AG-UI run and return its streaming response.

    The caller owns the run guard: this only builds the response, and the stream it wraps is
    still running when it returns.

    :return: ``(response, run_id)`` -- the open AG-UI stream, and the id later log lines quote.
    """
    context = runtime.context_store.context
    prepared = prepare_run(await request.body(), context, runtime.transcript)
    logger.info(
        "run started run_id=%s conversation_id=%s context_version=%s",
        prepared.run_id,
        prepared.conversation_id,
        prepared.context_version,
    )
    adapter = await AGUIAdapter.from_request(
        request_with_body(request, prepared.body),
        agent=runtime.agent,
        # 'server' mode attaches `ReinjectSystemPrompt(replace_existing=True)`, which
        # strips every `SystemPromptPart` from the history on each request. That is
        # where `SummarizingCompaction` keeps its summary, so server mode silently
        # deletes the summary the expensive tier just paid a model call to produce, and
        # the history re-summarizes on every subsequent request. The protection it
        # offers is redundant here anyway: `prepare_run` already reduces the request to
        # a single trusted user turn, so no client-supplied system prompt can reach the
        # model.
        manage_system_prompt="client",
    )
    # Recorded here rather than inferred from the run's history: the framework merges
    # this turn into a restored trailing request before any capability sees it, and the
    # adapter is the only place that still knows the turn on its own.
    await record_messages(
        runtime.transcript,
        prepared.run_id,
        adapter.sanitize_messages(adapter.messages),
    )
    recorder = TranscriptRecorder(
        log=runtime.transcript,
        context_store=runtime.context_store,
        conversation_id=prepared.conversation_id,
        run_id=prepared.run_id,
    )

    async def commit_context(result: AgentRunResult[Any]) -> None:
        # The authoritative end-of-run context: whatever compaction left behind, which
        # is exactly what the next run must be given.
        await runtime.context_store.commit(
            result.all_messages(),
            conversation_id=prepared.conversation_id,
        )

    events = adapter.run_stream(
        message_history=context.messages,
        conversation_id=prepared.conversation_id,
        run_id=prepared.run_id,
        capabilities=[recorder],
        on_complete=commit_context,
    )
    return (
        adapter.streaming_response(record_ui_events(events, log=runtime.ui_events, run_id=prepared.run_id)),
        prepared.run_id,
    )


def _hold_run_stream(
    response: Response,
    lease: RunLease,
    *,
    runtime: ConversationRuntime,
    run_id: str,
) -> _HoldStreamingResponse:
    """Hold the run lease through streaming and the final replication barrier."""
    inner = cast(StreamingResponse, response)
    existing_background = inner.background

    async def generate() -> AsyncIterator[str | bytes | memoryview]:
        lease.mark_entered()
        try:
            async for chunk in inner.body_iterator:
                yield chunk
        finally:
            # The barrier makes a normally completed Runtime disposable. A failed flush must
            # still release the lease: local files remain durable and the background replicator
            # keeps retrying, while `/health` exposes that the control plane is behind.
            try:
                if existing_background is not None:
                    await existing_background()
                if not await runtime.flush_replication():
                    logger.warning(
                        "releasing the run guard while the control plane is still behind; "
                        "this Runtime is not safe to discard yet"
                    )
            finally:
                lease.release()
                # Reached on a client disconnect as well as on a completed turn, so this says
                # the stream is over and not that the run succeeded.
                logger.info("run stream closed run_id=%s", run_id)

    headers = {**dict(inner.headers), **SSE_RESPONSE_HEADERS}
    return _HoldStreamingResponse(
        generate(),
        lease,
        status_code=inner.status_code,
        media_type=inner.media_type or "text/event-stream",
        headers=headers,
    )


def _drain(log: AppendLog, since: int, limit: int) -> JSONResponse:
    """Return one page of an append-only channel, plus the cursor to resume from."""
    if since < 0:
        raise HTTPException(status_code=422, detail="since must be a non-negative integer.")
    if not 1 <= limit <= settings.MAX_DRAIN_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=f"limit must be between 1 and {settings.MAX_DRAIN_LIMIT}.",
        )
    try:
        records = log.read_since(since, limit)
    except AppendLogError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(
        {
            "since": since,
            "last_seq": log.last_seq,
            "records": log.dump(records),
        }
    )
