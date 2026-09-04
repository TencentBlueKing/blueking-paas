"""Process logging: sandbox labels arrive on records, credentials do not."""

import logging

import pytest

from app_spark_agent import settings
from app_spark_agent.masking import SECRET_PLACEHOLDER
from app_spark_agent.observability import (
    LOG_FORMAT,
    LOGGER_NAME,
    UNLABELLED,
    SandboxLabelFilter,
    SecretMaskingFilter,
    configure_logging,
    log,
)

RUNTIME_TOKEN = "runtime-token-0123456789"


@pytest.fixture
def labelled_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SESSION_ID", "sess-demo")
    monkeypatch.setattr(settings, "TENANT_ID", "tenant-demo")


def make_record(message: str, args: object = ()) -> logging.LogRecord:
    return logging.LogRecord(
        name=LOGGER_NAME,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=None,
    )


def test_a_record_carries_the_sandbox_labels(
    labelled_sandbox: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Session and tenant must be searchable, so they ride on the record itself."""
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log.info("something happened")

    record = caplog.records[-1]
    assert record.session_id == "sess-demo"
    assert record.tenant_id == "tenant-demo"


def test_an_unlabelled_sandbox_still_formats(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Both labels are optional in the contract, and a blank field reads as a bug downstream."""
    monkeypatch.setattr(settings, "SESSION_ID", "")
    monkeypatch.setattr(settings, "TENANT_ID", "")

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log.info("something happened")

    record = caplog.records[-1]
    assert record.session_id == UNLABELLED
    assert record.tenant_id == UNLABELLED
    assert logging.Formatter(LOG_FORMAT).format(record).count(UNLABELLED) >= 2


def test_labels_are_read_when_the_record_is_made(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The adapter is built at import, long before the sandbox labels are known."""
    monkeypatch.setattr(settings, "SESSION_ID", "sess-late")
    monkeypatch.setattr(settings, "TENANT_ID", "tenant-late")

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log.info("late binding")

    assert caplog.records[-1].session_id == "sess-late"


def test_a_caller_can_override_a_label(labelled_sandbox: None, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log.info("explicit", extra={"session_id": "sess-explicit"})

    record = caplog.records[-1]
    assert record.session_id == "sess-explicit"
    assert record.tenant_id == "tenant-demo"


def test_this_logger_masks_before_any_handler_sees_the_record(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Masking only at the configured handler would leave the value on the record.

    Anything else holding a handler -- a host application, a test's capture, an exporter added
    later -- reads the record, not the line this module's handler printed.
    """
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        log.info("conversation_id=%s", f"conversation-{RUNTIME_TOKEN}")

    message = caplog.records[-1].getMessage()
    assert RUNTIME_TOKEN not in message
    assert SECRET_PLACEHOLDER in message


def test_the_masking_filter_hides_a_credential_in_the_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    record = make_record(f"token is {RUNTIME_TOKEN}")

    assert SecretMaskingFilter().filter(record) is True
    assert record.getMessage() == f"token is {SECRET_PLACEHOLDER}"


def test_the_masking_filter_hides_a_credential_in_the_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Masking the formatted line instead would run after the handler already has the values."""
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    record = make_record("token is %s and count is %s", (RUNTIME_TOKEN, 3))

    SecretMaskingFilter().filter(record)

    assert record.getMessage() == f"token is {SECRET_PLACEHOLDER} and count is 3"


def test_a_foreign_record_gets_the_labels_it_lacks(labelled_sandbox: None) -> None:
    """Uvicorn's records never pass through the adapter, and the formatter needs both fields."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="GET /health 200",
        args=(),
        exc_info=None,
    )

    assert SandboxLabelFilter().filter(record) is True
    assert logging.Formatter(LOG_FORMAT).format(record).endswith("GET /health 200")
    assert record.session_id == "sess-demo"


def test_configuring_twice_does_not_duplicate_output() -> None:
    """A repeated call must replace its own handler, and leave the host application's alone."""
    root = logging.getLogger()
    foreign = logging.NullHandler()
    original_handlers = list(root.handlers)
    original_level = root.level
    root.addHandler(foreign)
    try:
        configure_logging()
        after_first = list(root.handlers)
        configure_logging()
        after_second = list(root.handlers)

        assert len(after_second) == len(after_first)
        assert foreign in after_second
        assert sum(handler.name == LOGGER_NAME for handler in after_second) == 1
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_uvicorn_logs_are_routed_through_the_masking_handler() -> None:
    """Uvicorn's own handlers would print an unmasked second copy of every line."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    uvicorn_logger = logging.getLogger("uvicorn.access")
    original_uvicorn = list(uvicorn_logger.handlers)
    original_propagate = uvicorn_logger.propagate
    uvicorn_logger.addHandler(logging.NullHandler())
    try:
        configure_logging()

        assert uvicorn_logger.handlers == []
        assert uvicorn_logger.propagate is True
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
        uvicorn_logger.handlers = original_uvicorn
        uvicorn_logger.propagate = original_propagate
