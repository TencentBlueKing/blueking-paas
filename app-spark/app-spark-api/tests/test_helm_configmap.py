"""An omitted Helm value must preserve application defaults, without losing explicit overrides."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from dynaconf.base import LazySettings
from dynaconf.vendor.ruamel.yaml import YAML

HELM = shutil.which("helm")
CHART = Path(__file__).resolve().parents[1] / "charts" / "app-spark-api"
pytestmark = pytest.mark.skipif(HELM is None, reason="Helm is required for chart rendering tests")


def _render_configmap(overrides: dict[str, Any] | None = None) -> dict[str, str]:
    command = [HELM or "helm", "template", "spark-test", str(CHART)]
    command.extend(["--show-only", "templates/general-envs-configmap.yaml"])
    for key, value in (overrides or {}).items():
        command.extend(["--set-json", f"{key}={json.dumps(value)}"])
    rendered = subprocess.run(command, check=True, capture_output=True, text=True)
    return YAML(typ="safe").load(rendered.stdout)["data"]


def test_default_configmap_omits_optional_settings():
    data = _render_configmap()
    for setting in ("DEBUG", "LANGUAGE_CODE", "LANGUAGES", "TIME_ZONE", "STATIC_URL", "AGENT_RUNTIME_PROVIDER"):
        assert f"APP_SPARK_API_{setting}" not in data
    assert "APP_SPARK_API_DATABASE_HOST" in data
    assert "APP_SPARK_API_BKAUTH_TOKEN_APP_CODE" in data
    assert "APP_SPARK_API_AGENT_RUNTIME_PROVIDER_CONFIG" in data
    assert "APP_SPARK_API_FORCE_SCRIPT_NAME" in data


def test_default_force_script_name_matches_ingress_prefix(monkeypatch):
    data = _render_configmap()
    monkeypatch.setenv("CHART_TEST_FORCE_SCRIPT_NAME", data["APP_SPARK_API_FORCE_SCRIPT_NAME"])
    loaded = LazySettings(environments=False, envvar_prefix="CHART_TEST", settings_files=[])
    assert loaded.get("FORCE_SCRIPT_NAME") == "/api-svc"


def test_null_groups_and_values_are_omitted():
    data = _render_configmap(
        dict.fromkeys(["django", "externalDatabase", "bkAuth", "agent", "enableMultiTenantMode", "loginFull"])
    )
    assert not any(key.startswith("APP_SPARK_API_") for key in data)


@pytest.mark.parametrize(
    ("key", "value", "setting"),
    [
        ("django.debug", False, "DEBUG"),
        ("django.dataUploadMaxMemorySize", 0, "DATA_UPLOAD_MAX_MEMORY_SIZE"),
        ("django.secretKey", "", "SECRET_KEY"),
        ("django.allowedHosts", [], "ALLOWED_HOSTS"),
        ("django.forceScriptName", "/svc", "FORCE_SCRIPT_NAME"),
        ("defaultCacheConfig", {}, "DEFAULT_CACHE_CONFIG"),
        ("django.languageCode", "en", "LANGUAGE_CODE"),
        ("externalDatabase.password", "00123", "DATABASE_PASSWORD"),
        ("blobstoreBkrepoConfig", {"PROJECT": "test", "PASSWORD": "true"}, "BLOBSTORE_BKREPO_CONFIG"),
    ],
)
def test_explicit_values_survive_dynaconf(monkeypatch, key, value, setting):
    data = _render_configmap({key: value})
    monkeypatch.setenv(f"CHART_TEST_{setting}", data[f"APP_SPARK_API_{setting}"])
    loaded = LazySettings(environments=False, envvar_prefix="CHART_TEST", settings_files=[])
    assert loaded.get(setting) == value


def test_null_leaf_preserves_application_fallback(monkeypatch):
    data = _render_configmap({"django.secretKey": None, "django.languageCode": None, "django.forceScriptName": None})
    assert "APP_SPARK_API_SECRET_KEY" not in data
    assert "APP_SPARK_API_LANGUAGE_CODE" not in data
    assert "APP_SPARK_API_FORCE_SCRIPT_NAME" not in data
    for key, value in data.items():
        if key.startswith("APP_SPARK_API_"):
            monkeypatch.setenv(key.replace("APP_SPARK_API_", "CHART_TEST_", 1), value)
    loaded = LazySettings(environments=False, envvar_prefix="CHART_TEST", settings_files=[])
    assert loaded.get("LANGUAGE_CODE", "zh-hans") == "zh-hans"
