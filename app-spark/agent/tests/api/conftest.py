"""Started Runtime clients supplied to the API tests as pytest fixtures."""

from collections.abc import Iterator, Sequence
from contextlib import ExitStack
from itertools import count
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.models.function import FunctionModel

from app_spark_agent import settings
from tests.api.support import MODEL_API_KEY, RUNTIME_TOKEN, ApiFactory, build_test_client
from tests.support.fake_models import text_model

# Split into more than one chunk on purpose: every test inherits a model that actually streams,
# so a broken delta path cannot pass unnoticed just because the reply arrived in one piece.
DEFAULT_REPLY: tuple[str, ...] = ("he", "llo")


@pytest.fixture(autouse=True)
def sandbox_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give API tests the sandbox contract a real injection would provide."""
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "MODEL_API_KEY", MODEL_API_KEY)
    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "https://model-gateway.test/v1")
    monkeypatch.setattr(settings, "APP_PORT", settings.DEFAULT_APP_PORT)
    # A short idle timeout in a developer .env must not os._exit during TestClient.
    monkeypatch.setattr(settings, "IDLE_TIMEOUT_SECONDS", 0)
    # Both labels are optional in the contract, so the default here is the unlabelled case a
    # test must opt out of rather than the other way round.
    monkeypatch.setattr(settings, "SESSION_ID", "")
    monkeypatch.setattr(settings, "TENANT_ID", "")


@pytest.fixture
def make_api(tmp_path: Path) -> Iterator[ApiFactory]:
    """Return a factory for started Runtimes, each with its own workspace and state directory.

    A test may build more than one: a second Runtime reopening its own state is a different
    scenario, not a variation on the first, so nothing is shared between them.
    """
    with ExitStack() as lifespans:
        runtimes = count()

        def factory(
            *,
            model: FunctionModel | None = None,
            capabilities: Sequence[AbstractCapability[object]] = (),
            tools: Sequence[Any] = (),
        ) -> TestClient:
            root = tmp_path / f"runtime-{next(runtimes)}"
            root.mkdir()
            client = build_test_client(
                root,
                model=model if model is not None else text_model(DEFAULT_REPLY),
                capabilities=capabilities,
                tools=tools,
            )
            # Entering the client runs the application's lifespan the way an ASGI server would,
            # and keeps every request of one test on a single event loop.
            lifespans.enter_context(client)
            return client

        yield factory


@pytest.fixture
def api(make_api: ApiFactory) -> TestClient:
    """A started Runtime whose model streams :data:`DEFAULT_REPLY` as one assistant message."""
    return make_api()
