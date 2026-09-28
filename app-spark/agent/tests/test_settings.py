"""就绪门闩：fake、只配 MODEL_API_KEY 的直连、或齐全的网关三件套。"""

import pytest
from pytest import MonkeyPatch

from app_spark_agent import settings


@pytest.fixture
def ready(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", "user-token")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "https://bkaidev.test/v1")


def test_listed_model_has_an_explicit_profile(ready: None) -> None:
    profile = settings.openai_capability_profile()

    assert settings.model_profile() == "deepseek"
    assert settings.is_model_ready() is True
    assert profile is not None
    assert profile["supports_tools"] is True
    assert profile["supports_json_schema_output"] is True


def test_unknown_model_has_no_capability_profile(ready: None, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_NAME", "not-a-listed-model")

    assert settings.openai_capability_profile() is None


def test_unknown_model_is_not_inferred(ready: None, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_NAME", "some-new-vendor-model")

    assert settings.model_profile() is None
    assert settings.is_model_ready() is False


def test_a_fake_model_is_ready_without_gateway_settings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL", "fake:write-file")
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "MODEL_NAME", "")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "")

    assert settings.is_model_ready() is True


def test_api_key_alone_is_the_direct_provider(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL", "deepseek:deepseek-v4-flash")
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "MODEL_API_KEY", "provider-key")
    monkeypatch.setattr(settings, "MODEL_NAME", "")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "")

    assert settings.gateway_access_token() is None
    assert settings.uses_direct_provider() is True
    assert settings.model_mode() == settings.ModelMode.DIRECT
    assert settings.is_model_ready() is True


def test_api_key_does_not_complete_a_partial_gateway(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "MODEL_API_KEY", "provider-key")
    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "https://bkaidev.test/v1")

    assert settings.gateway_access_token() is None
    assert settings.uses_direct_provider() is False
    assert settings.is_model_ready() is False


def test_whitespace_token_is_absent(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", "   ")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "https://bkaidev.test/v1")

    assert settings.gateway_access_token() is None
    assert settings.is_model_ready() is False


def test_direct_provider_is_only_for_api_key_without_gateway(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "MODEL_API_KEY", "provider-key")
    monkeypatch.setattr(settings, "MODEL_NAME", "")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "")

    assert settings.uses_direct_provider() is True

    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")

    assert settings.uses_direct_provider() is False
