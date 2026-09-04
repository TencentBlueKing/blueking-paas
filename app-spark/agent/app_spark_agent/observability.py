"""Process logging: sandbox labels on every record, credentials on none.

``APP_SPARK_AGENT_SESSION_ID`` and ``APP_SPARK_AGENT_TENANT_ID`` exist only to make one sandbox's output findable
among many, so they belong on every record rather than on the handful of call sites that
remember to pass them. They are labels and nothing more: no code branches on either.

Masking is applied twice on purpose: on this module's logger, so a record never carries a
credential in the first place, and on the handler, so records from uvicorn and from any other
library are covered as well. The leak worth defending against is the one written by code that
never heard of this module.
"""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

from app_spark_agent import settings
from app_spark_agent.masking import mask_payload, mask_text

LOGGER_NAME = "app_spark_agent"

# Rendered when the injection layer left the label out. An empty field would silently look
# like a formatting bug in whatever collects these lines.
UNLABELLED = "-"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s session_id=%(session_id)s tenant_id=%(tenant_id)s %(message)s"

# Their records reach the root handler by propagation once their own handlers are removed;
# leaving both in place would print every line twice and skip the masking filter on one copy.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def sandbox_labels() -> dict[str, str]:
    """Return the sandbox labels to stamp on a log record.

    Read per call, so a value patched in tests or resolved late still shows up.
    """
    return {
        "session_id": settings.SESSION_ID or UNLABELLED,
        "tenant_id": settings.TENANT_ID or UNLABELLED,
    }


class SandboxLabelFilter(logging.Filter):
    """Give records that came from elsewhere the label fields the formatter expects.

    Attached to the handler rather than to a logger: uvicorn's records never pass through
    :data:`log`, and a formatter missing one key raises instead of printing the line.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Fill in any label the record does not already carry, and keep the record."""
        for field, value in sandbox_labels().items():
            if not hasattr(record, field):
                setattr(record, field, value)
        return True


class SecretMaskingFilter(logging.Filter):
    """Replace credential values in a record, in place.

    Both the template and its arguments are masked. Masking only the rendered line would mean
    rendering first, which is what a handler does after every filter has already run -- and
    would leave the values on the record for anything else that reads it.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask the record in place and keep it."""
        if isinstance(record.msg, str):
            record.msg = mask_text(record.msg)
        if record.args:
            # `args` is a tuple for positional formatting and a mapping for `%(name)s`
            # templates; `mask_payload` walks both and leaves non-string leaves alone.
            record.args = mask_payload(record.args)
        return True


class SandboxLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger that stamps the sandbox labels onto each record as it is created.

    Set at creation instead of by a handler filter so the fields survive anywhere records are
    inspected rather than printed -- ``caplog`` in the tests, and any future handler that does
    not go through :func:`configure_logging`.
    """

    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> tuple[Any, MutableMapping[str, Any]]:
        """Merge the sandbox labels into the record's ``extra``, without overriding a caller."""
        extra = {**sandbox_labels(), **dict(kwargs.get("extra") or {})}
        kwargs["extra"] = extra
        return msg, kwargs


_logger = logging.getLogger(LOGGER_NAME)
# Masked where the record is made, not only where it is written. A record that still holds the
# value leaks through every other handler -- a host application's, a test's capture, anything
# added later -- and a logger filter runs before any handler is called.
_logger.addFilter(SecretMaskingFilter())

log = SandboxLoggerAdapter(_logger, {})


def configure_logging(level: int = logging.INFO) -> None:
    """Send this process's logs to stderr with sandbox labels and credentials masked.

    Idempotent: a repeated call replaces the handler it installed rather than adding a second
    one, so an entry point that runs twice does not double every line.

    :param level: Threshold for the root logger.
    """
    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, "_app_spark_agent_handler", False):
            root.removeHandler(existing)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    # Labels first: masking must run on a record the formatter can already render, and the
    # label values themselves are not credentials.
    handler.addFilter(SandboxLabelFilter())
    handler.addFilter(SecretMaskingFilter())
    handler.set_name(LOGGER_NAME)
    # Marks ownership so a second call can tell this handler from one a host application added.
    handler._app_spark_agent_handler = True  # type: ignore[attr-defined]

    root.addHandler(handler)
    root.setLevel(level)

    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
