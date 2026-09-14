"""Credential masking: what counts as a secret, and what a masked document looks like."""

from typing import Any

import pytest

from app_spark_agent import settings
from app_spark_agent.masking import SECRET_PLACEHOLDER, mask_payload, mask_text, secret_values

RUNTIME_TOKEN = "runtime-token-0123456789"
MODEL_API_KEY = "model-api-key-0123456789"
BK_AIDEV_ACCESS_TOKEN = "aidev-access-token-0123456789"
CONTROL_PLANE_TOKEN = "control-plane-token-0123456789"


@pytest.fixture
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure every outbound credential with distinct values."""
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", RUNTIME_TOKEN)
    monkeypatch.setattr(settings, "MODEL_API_KEY", MODEL_API_KEY)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", BK_AIDEV_ACCESS_TOKEN)
    monkeypatch.setattr(settings, "CONTROL_PLANE_TOKEN", CONTROL_PLANE_TOKEN)


def test_every_configured_credential_is_masked(credentials: None) -> None:
    text = f"token={RUNTIME_TOKEN} key={MODEL_API_KEY} aidev={BK_AIDEV_ACCESS_TOKEN} cp={CONTROL_PLANE_TOKEN}"

    masked = mask_text(text)

    assert RUNTIME_TOKEN not in masked
    assert MODEL_API_KEY not in masked
    assert BK_AIDEV_ACCESS_TOKEN not in masked
    assert CONTROL_PLANE_TOKEN not in masked
    assert masked == (
        f"token={SECRET_PLACEHOLDER} key={SECRET_PLACEHOLDER} aidev={SECRET_PLACEHOLDER} cp={SECRET_PLACEHOLDER}"
    )


def test_key_names_survive_masking(credentials: None) -> None:
    """Names are what makes a log line or a settings table readable; only values are secret."""
    text = "APP_SPARK_AGENT_RUNTIME_TOKEN and APP_SPARK_AGENT_MODEL_API_KEY are set"

    assert mask_text(text) == text


def test_an_unset_credential_masks_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty value must not turn into a match against every string in sight."""
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", "")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "CONTROL_PLANE_TOKEN", None)

    assert secret_values() == ()
    assert mask_text("nothing to hide") == "nothing to hide"


def test_the_longest_credential_is_masked_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """One credential containing another must not leave the remainder of the longer one behind.

    Masking the short value first would rewrite the middle of the long one and let its head and
    tail through, which reads as a partial leak rather than as a masked value.
    """
    short = "secret"
    long = f"prefix-{short}-suffix"
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", short)
    monkeypatch.setattr(settings, "MODEL_API_KEY", long)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "CONTROL_PLANE_TOKEN", None)

    assert secret_values() == (long, short)
    assert mask_text(f"value={long}") == f"value={SECRET_PLACEHOLDER}"


def test_credentials_are_read_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """A value captured at import would keep masking whatever the environment held back then."""
    monkeypatch.setattr(settings, "RUNTIME_TOKEN", "first")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "CONTROL_PLANE_TOKEN", None)
    assert mask_text("first") == SECRET_PLACEHOLDER

    monkeypatch.setattr(settings, "RUNTIME_TOKEN", "second")

    assert mask_text("first") == "first"
    assert mask_text("second") == SECRET_PLACEHOLDER


def test_a_whole_document_is_walked(credentials: None) -> None:
    payload: dict[str, Any] = {
        "type": "TEXT_MESSAGE_CONTENT",
        "delta": f"the key is {MODEL_API_KEY}",
        "nested": {"headers": [f"Bearer {RUNTIME_TOKEN}", "Accept: text/event-stream"]},
        "seq": 7,
        "done": False,
        "missing": None,
    }

    masked = mask_payload(payload)

    assert masked == {
        "type": "TEXT_MESSAGE_CONTENT",
        "delta": f"the key is {SECRET_PLACEHOLDER}",
        "nested": {"headers": [f"Bearer {SECRET_PLACEHOLDER}", "Accept: text/event-stream"]},
        "seq": 7,
        "done": False,
        "missing": None,
    }


def test_tuples_keep_their_shape(credentials: None) -> None:
    """Log record arguments arrive as a tuple, and `%`-formatting rejects a list."""
    masked = mask_payload((f"Bearer {RUNTIME_TOKEN}", 3))

    assert masked == (f"Bearer {SECRET_PLACEHOLDER}", 3)
    assert isinstance(masked, tuple)
