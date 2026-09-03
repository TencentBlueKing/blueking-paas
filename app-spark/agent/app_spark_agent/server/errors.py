"""Application error handlers: 409 mapping, and credential masking on HTTP error bodies."""

from typing import cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse, Response

from app_spark_agent.masking import mask_payload, mask_text
from app_spark_agent.server.runtime import RuntimeBusyError


async def busy_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    """Answer a refused exclusive operation with a 409.

    Registered on the application rather than repeated in every view.
    """
    return JSONResponse({"detail": mask_text(str(exc))}, status_code=status.HTTP_409_CONFLICT)


async def masked_http_exception_handler(request: Request, exc: Exception) -> Response:
    """Answer an ``HTTPException`` with its detail masked.

    Several views build a detail out of an exception's own text, and an exception raised deep
    in a library can quote whatever string it was handed. Masking here covers all of them at
    once instead of asking every raise site to remember.
    """
    http_exc = cast(HTTPException, exc)
    return JSONResponse(
        {"detail": mask_payload(http_exc.detail)},
        status_code=http_exc.status_code,
        headers=http_exc.headers,
    )


async def masked_validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Answer a request-validation failure with the echoed input masked.

    FastAPI's default reply quotes the rejected input, so a client that puts its token in the
    body would get it back in the error -- and into whatever logs that response.
    """
    validation_exc = cast(RequestValidationError, exc)
    return JSONResponse(
        {"detail": mask_payload(jsonable_encoder(validation_exc.errors()))},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register handlers that map domain conflicts to 409 and mask credentials in HTTP error bodies."""
    app.add_exception_handler(RuntimeBusyError, busy_conflict_handler)
    app.add_exception_handler(HTTPException, masked_http_exception_handler)
    app.add_exception_handler(RequestValidationError, masked_validation_exception_handler)
