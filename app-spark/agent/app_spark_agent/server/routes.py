"""HTTP views: health, drain, context, and the AG-UI run."""

import json
from collections.abc import Callable
from typing import Annotated, Any, cast

from ag_ui.core import RunErrorEvent
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic_ai.exceptions import RunCancelled
from pydantic_ai.run import AgentRunResult
from pydantic_ai.ui.ag_ui import AGUIAdapter
from starlette.responses import JSONResponse, Response

from app_spark_agent import VERSION, settings
from app_spark_agent.git import GitError

# Imported under a different name: `log` already means "append-only channel" in this module.
from app_spark_agent.observability import log as logger
from app_spark_agent.recorder import TranscriptRecorder, record_messages
from app_spark_agent.server.run_input import prepare_run, request_with_body
from app_spark_agent.server.run_task import RunStopper, RuntimeClosingError
from app_spark_agent.server.runtime import ConversationRuntime, RuntimeBusyError
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

SSE_RESPONSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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

    ``workspace`` answers the same question for the files rather than the conversation, and it
    has to be asked separately: a turn's stream ending means its files are *committed locally*,
    never that they reached the Git remote. Its ``unsaved_seconds`` and ``push_failures`` are
    there so that "is this Runtime falling behind" is a query rather than a log-reading exercise.
    """
    context = runtime.context_store.context
    replicator = runtime.replicator
    saver = runtime.saver
    return {
        "version": VERSION,
        "model_ready": settings.is_model_ready(),
        "running": runtime.run_guard.busy,
        "run_id": runtime.runs.current.run_id if runtime.runs.current is not None else None,
        "dev_server_status": await runtime.app_supervisor.dev_server_status(),
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
        "workspace_persisted": saver is not None,
        "workspace_save_pending": saver is not None and saver.status.outstanding,
        "workspace": saver.status.as_payload() if saver is not None else None,
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


@router.put("/cursors", dependencies=[Depends(require_bearer)])
async def adopt_cursors(
    runtime: RuntimeDep,
    log_seq: int = Query(ge=0),
    ui_event_seq: int = Query(ge=0),
) -> JSONResponse:
    """Tell an empty Runtime where a conversation's history stands, with no context to inject.

    The counterpart of ``PUT /context`` for a conversation whose entries reached the control
    plane but whose first context never did. Both cursors are required: unlike a context
    restore there is nothing else in the request, so omitting one can only be a mistake.

    :param log_seq: Sequence number the raw transcript should continue from.
    :param ui_event_seq: Sequence number the AG-UI event history should continue from.
    """
    async with runtime.run_guard.exclusive():
        try:
            await runtime.adopt_numbering(log_seq=log_seq, ui_event_seq=ui_event_seq)
        except (ConversationStateConflict, AppendLogError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CursorStateError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse({"log_seq": runtime.transcript.last_seq, "ui_event_seq": runtime.ui_events.last_seq})


@router.post("/workspace/restore", dependencies=[Depends(require_bearer)])
async def restore_workspace(runtime: RuntimeDep, commit: str = Query(min_length=7)) -> JSONResponse:
    """Bring the workspace to a checkpoint, before any context is injected or any run accepted.

    Files first is not a preference, it is the order the restore has to happen in: injecting the
    conversation first would leave a window in which the Runtime would accept a turn whose model
    remembers files that are not on disk yet.

    Held under the run guard for the same reason ``PUT /context`` is -- rewriting the working
    tree underneath a run in progress would corrupt both.

    :param commit: The checkpoint's commit SHA.
    :return: What had to be done; see ``RestoreOutcome``. ``superseded`` is a success, and means
        the Project has been developed in another conversation since and that work was kept.
    """
    if runtime.saver is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Runtime has no Git repository, so it has nothing to restore from.",
        )
    async with runtime.run_guard.exclusive():
        try:
            outcome = await runtime.saver.restore_to(commit)
        except GitError as exc:
            # Deliberately loud, and deliberately not a silent empty workspace: a Runtime that
            # started on the wrong files does not show it until several turns later.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"The workspace could not be restored to {commit}: {exc}",
            ) from exc
    return JSONResponse({"outcome": str(outcome), "head": runtime.saver.status.local_sha})


@router.post("/runs", dependencies=[Depends(require_bearer)])
async def run(
    request: Request,
    runtime: RuntimeDep,
    allow_unsaved: bool = Query(default=False),
) -> Response:
    """Start one conversation turn and stream it back as AG-UI events.

    The turn runs as a task of its own: this response only follows it. A client that hangs up
    stops receiving events and nothing else -- the turn runs to its end, and what it produced
    reaches the control plane the same way as for a client that stayed. Stopping a turn is
    ``POST /runs/{run_id}/stop``. Refused with ``503`` once shutdown has begun.

    :param allow_unsaved: Proceed even though the previous turn's files have not reached the Git
        remote. The escape hatch from the gate below; the next turn's changes pile on top of the
        unsaved ones, which is a choice for the user to make rather than one to make for them.
    """
    if not settings.is_model_ready():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not ready")
    if not allow_unsaved:
        await _require_previous_turn_saved(runtime)
    lease = await runtime.run_guard.try_acquire()
    if lease is None:
        raise RuntimeBusyError("An Agent run is already in progress.")

    try:
        return await _start_run(runtime, request, release=lease.release)
    except RuntimeClosingError as exc:
        lease.release()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except BaseException:
        lease.release()
        raise


@router.post("/runs/{run_id}/stop", dependencies=[Depends(require_bearer)])
async def stop_run(run_id: str, runtime: RuntimeDep) -> JSONResponse:
    """Ask the turn in progress to stop, and return without waiting for it to.

    The turn winds down the way a finished one does: its event stream ends with
    ``RUN_FINISHED``, what it had done so far is committed as the conversation's context, and
    its files are committed as an interrupted turn. ``running`` on ``/health`` going false is
    the sign it is over.

    :param run_id: The turn to stop. Naming it is what keeps a late request from stopping the
        turn after it.
    :return: ``202`` while the turn winds down, also for a repeated request; ``404`` when
        ``run_id`` is not the turn in progress, including one that has already ended.
    """
    if not runtime.runs.request_stop(run_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such run in progress.")
    logger.info("run stop requested run_id=%s", run_id)
    return JSONResponse({"run_id": run_id, "stopping": True}, status_code=status.HTTP_202_ACCEPTED)


async def _require_previous_turn_saved(runtime: ConversationRuntime) -> None:
    """Hold the next turn back until the previous one's files are on the Git remote.

    The first version keeps one writer's worth of change in flight at a time: letting a second
    turn edit files whose predecessor has not been saved makes "what does this checkpoint
    contain" a much harder question than it needs to be.

    Refused with the same 409 the run guard uses, because from the client's side both mean "not
    now, try again" -- but with a distinct ``code`` and an explicit way out, since a network
    partition would otherwise make this rule an indefinite lockout rather than a delay.

    :raises HTTPException: 409 when the previous turn is still unsaved after the wait.
    """
    if runtime.saver is None:
        return
    if await runtime.await_workspace_saved(timeout_seconds=settings.GIT_SAVE_WAIT_TIMEOUT_SECONDS):
        return
    status_payload = runtime.saver.status
    logger.warning(
        "refusing a new run: the previous turn is still unsaved after %.0fs (%s)",
        settings.GIT_SAVE_WAIT_TIMEOUT_SECONDS,
        status_payload.state,
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "workspace_save_pending",
            "message": (
                "The previous turn's files have not reached the Git repository yet. Wait and "
                "retry, or repeat this request with ?allow_unsaved=true to continue without "
                "saving that work first."
            ),
            "workspace": status_payload.as_payload(),
        },
    )


async def _start_run(
    runtime: ConversationRuntime,
    request: Request,
    *,
    release: Callable[[], None],
) -> StreamingResponse:
    """Validate one AG-UI run, start it, and return a response following its events.

    :param release: Hands the run guard back. From the moment the run has started it belongs to
        the run's task, which calls it once the turn is over; until then the caller still owns it.
    :return: The open AG-UI stream.
    """
    context = runtime.context_store.context
    prepared = prepare_run(await request.body(), context, runtime.transcript)

    # 额度按轮清零：防的是一轮里反复重试，不是给整个会话设总量。
    runtime.launch_tool.begin_run()
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
    stopper = RunStopper()
    # Set by the agent itself, not inferred from the stop request: a stop that lands as the
    # turn is finishing anyway is a no-op, and that turn did complete.
    cancelled = False

    async def commit_context(result: AgentRunResult[Any]) -> None:
        # The authoritative end-of-run context: whatever compaction left behind, which
        # is exactly what the next run must be given.
        await runtime.context_store.commit(
            result.all_messages(),
            conversation_id=prepared.conversation_id,
        )

    async def commit_stopped_context(stopped: RunCancelled) -> None:
        nonlocal cancelled
        cancelled = True
        # A stopped turn still happened: its files are on disk, and the next turn's model has
        # to know what it did to them. pydantic-ai has already closed out the tool calls that
        # never returned, so this history can be handed to a model as it is.
        await runtime.context_store.commit(
            stopped.all_messages(),
            conversation_id=prepared.conversation_id,
        )

    async def finish(stream_completed: bool) -> None:
        # Local, fast, and deterministic, which is what makes it safe here: this also runs for
        # a turn cancelled outright at shutdown, where a network push could not be relied on
        # to finish. Pushing is the background saver's job.
        await runtime.save_workspace(
            run_id=prepared.run_id,
            conversation_id=prepared.conversation_id,
            completed=stream_completed and not cancelled,
        )
        # Shutting down: the lifespan drains right after this, against the deadline it has left,
        # which a full flush timeout here would overrun.
        if runtime.runs.closing:
            return
        # The barrier makes a normally completed Runtime disposable. A failed flush must still
        # release the guard: local files remain durable and the background replicator keeps
        # retrying, while `/health` exposes that the control plane is behind.
        if not await runtime.flush_replication():
            logger.warning(
                "releasing the run guard while the control plane is still behind; "
                "this Runtime is not safe to discard yet"
            )

    events = adapter.run_stream(
        message_history=context.messages,
        conversation_id=prepared.conversation_id,
        run_id=prepared.run_id,
        capabilities=[recorder, stopper],
        on_complete=commit_context,
        on_cancel=commit_stopped_context,
    )
    encoder = adapter.build_event_stream()
    run = runtime.runs.start(
        run_id=prepared.run_id,
        stopper=stopper,
        events=encoder.encode_stream(record_ui_events(events, log=runtime.ui_events, run_id=prepared.run_id)),
        finish=finish,
        release=release,
        error_frame=lambda message: encoder.encode_event(RunErrorEvent(message=message)),
    )
    return StreamingResponse(
        run.events.subscribe(),
        media_type=encoder.content_type,
        headers={**(encoder.response_headers or {}), **SSE_RESPONSE_HEADERS},
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
