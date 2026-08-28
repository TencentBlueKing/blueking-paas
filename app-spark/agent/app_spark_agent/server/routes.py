"""HTTP views: the only module that speaks in requests, responses, and status codes."""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from pydantic_ai.run import AgentRunResult
from pydantic_ai.ui.ag_ui import AGUIAdapter
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, Response

from app_spark_agent import settings
from app_spark_agent.recorder import TranscriptRecorder, record_messages
from app_spark_agent.server.run_input import prepare_run, request_with_body
from app_spark_agent.server.runtime import ConversationRuntime
from app_spark_agent.state import (
    AppendLog,
    AppendLogError,
    ConversationContext,
    ConversationStateConflict,
    ConversationStateError,
)
from app_spark_agent.ui_events import record_ui_events

router = APIRouter()


def attach_runtime(app: FastAPI, runtime: ConversationRuntime) -> None:
    """Give ``app`` the conversation its views will serve."""
    app.state.conversation_runtime = runtime


def get_runtime(request: Request) -> ConversationRuntime:
    """Return the conversation this process serves."""
    # `Request.app` is typed as `Any` and `State` accepts arbitrary attributes, so the type has
    # to be restored by hand -- this is the one place that does it.
    return cast(ConversationRuntime, request.app.state.conversation_runtime)


RuntimeDep = Annotated[ConversationRuntime, Depends(get_runtime)]


async def busy_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    """Answer a refused exclusive operation with a 409.

    Registered on the application rather than repeated in every view.
    """
    return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_409_CONFLICT)


@router.get("/health")
async def health(runtime: RuntimeDep) -> dict[str, object]:
    """Report the conversation's identity and the cursor of every stream."""
    context = runtime.context_store.context
    return {
        "status": "ok",
        "model": settings.MODEL,
        "conversation_id": context.conversation_id,
        "context_version": context.context_version,
        "log_seq": runtime.transcript.last_seq,
        "ui_event_seq": runtime.ui_events.last_seq,
        "running": runtime.run_guard.busy,
    }


@router.get("/log")
async def read_log(
    runtime: RuntimeDep,
    since: int = Query(default=0),
    limit: int = Query(default=settings.DEFAULT_DRAIN_LIMIT),
) -> JSONResponse:
    """Return one page of the raw model transcript."""
    return _drain(runtime.transcript, since, limit)


@router.get("/ui-events")
async def read_ui_events(
    runtime: RuntimeDep,
    since: int = Query(default=0),
    limit: int = Query(default=settings.DEFAULT_DRAIN_LIMIT),
) -> JSONResponse:
    """Return one page of the AG-UI event history."""
    return _drain(runtime.ui_events, since, limit)


@router.get("/context")
async def read_context(runtime: RuntimeDep) -> JSONResponse:
    """Export the context the next run will be given, tagged with its version."""
    context = runtime.context_store.context
    return JSONResponse(
        context.as_payload(),
        headers={"ETag": str(context.context_version)},
    )


@router.put("/context")
async def restore_context(request: Request, runtime: RuntimeDep) -> JSONResponse:
    """Inject a cold context into an empty Runtime."""
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
            restored = await runtime.context_store.restore(context)
        except ConversationStateConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ConversationStateError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON context payload.") from exc
        return JSONResponse(
            restored.as_payload(),
            headers={"ETag": str(restored.context_version)},
        )


@router.post("/runs")
async def run(request: Request, runtime: RuntimeDep) -> Response:
    """Run one conversation turn and stream it back as AG-UI events."""
    # A refusal here becomes a 409 through `busy_conflict_handler`; the guard is not held
    # yet, so this call must stay outside the release-on-failure block below.
    await runtime.run_guard.acquire()

    # Held past the end of this handler: the guard is only released once the streaming
    # response finishes, so it is not a `with` block. Any failure before the response
    # exists must hand it back here, or the Runtime stays busy forever.
    try:
        response = await _start_run(runtime, request)
    except Exception:
        runtime.run_guard.release()
        raise

    existing_background = response.background

    async def finish_response() -> None:
        try:
            if existing_background is not None:
                await existing_background()
        finally:
            runtime.run_guard.release()

    response.background = BackgroundTask(finish_response)
    return response


async def _start_run(runtime: ConversationRuntime, request: Request) -> Response:
    """Validate one AG-UI run and return its streaming response.

    The caller owns the run guard: this only builds the response, and the stream it wraps is
    still running when it returns.
    """
    context = runtime.context_store.context
    prepared = prepare_run(await request.body(), context, runtime.transcript)
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
    return adapter.streaming_response(
        record_ui_events(events, log=runtime.ui_events, run_id=prepared.run_id)
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
