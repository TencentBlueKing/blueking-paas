"""就绪门闩：fake、只配 MODEL_API_KEY 的直连、或齐全的网关三件套（模型名不查表）。"""

import pytest
from marshmallow import ValidationError
from pytest import MonkeyPatch

from app_spark_agent import settings


@pytest.fixture
def ready(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BK_AIDEV_ACCESS_TOKEN", "user-token")
    monkeypatch.setattr(settings, "MODEL_API_KEY", None)
    monkeypatch.setattr(settings, "MODEL_NAME", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "MODEL_BASE_URL", "https://bkaidev.test/v1")


def test_the_gateway_profile_turns_every_capability_on() -> None:
    # 推断出的档会关掉 supports_tool_return_schema，保守档连工具调用都关，所以这四项必须显式全开。
    profile = settings.openai_capability_profile()

    assert profile["supports_tools"] is True
    assert profile["supports_json_schema_output"] is True
    assert profile["supports_json_object_output"] is True
    assert profile["supports_tool_return_schema"] is True


@pytest.mark.parametrize("name", ["deepseek-v4-flash", "hy3", "GLM-5_3-Online-32k"])
def test_any_model_name_completes_the_gateway(ready: None, monkeypatch: MonkeyPatch, name: str) -> None:
    monkeypatch.setattr(settings, "MODEL_NAME", name)

    assert settings.model_mode() == settings.ModelMode.GATEWAY
    assert settings.is_model_ready() is True


def test_a_blank_model_name_leaves_the_gateway_unready(ready: None, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MODEL_NAME", "   ")

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


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@pypi.example.com/simple",
        "https://token@pypi.example.com/simple",
        "ftp://pypi.example.com/simple",
        "pypi.example.com/simple",
    ],
)
def test_package_index_url_refuses_credentials_and_non_http(url: str) -> None:
    with pytest.raises(ValidationError):
        settings._validate_package_index_url(url)


def test_package_index_url_accepts_a_plain_https_url() -> None:
    settings._validate_package_index_url("https://pypi.example.com/simple")
