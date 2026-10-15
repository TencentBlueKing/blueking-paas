# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured
from svc_mysql.settings.kms import ENABLED_ENV_VAR, ENVELOPE_PATH_ENV_VAR, PRIVATE_KEY_ENV_VAR, get_env

DB_PASSWORD = "$HOME p@ss:/w#rd?"
SERVICES = [
    ("svc-mysql", "svc_mysql", "svc_mysql"),
    ("svc-bkrepo", "svc_bk_repo", "svc_bkrepo"),
    ("svc-rabbitmq", "svc_rabbitmq", "svc_rabbitmq"),
    ("svc-otel", "svc_otel", "svc_otel"),
]
CREDENTIALS = {
    "mysql": {instance: {"username": instance, "password": DB_PASSWORD} for _, _, instance in SERVICES},
    "encryption": {
        "bk_krill": {"secret_key": "krill-key"},
        "bk_krill_otel": {"secret_key": "otel-key"},
    },
    "jwt": {"services": {"client_key": "jwt-client-key"}},
    "django": {"svc_rabbitmq": {"secret_key": "rabbitmq-django-key"}},
    "bkapp_id_secret": {"default": {"app_code": "bk_paas3", "app_secret": "$app-secret"}},
}
BINDINGS = {
    "MYSQL_PASSWORD": "mysql.svc_mysql.password",
    "PAAS_SERVICE_JWT_CLIENTS_KEY": "jwt.services.client_key",
}


@pytest.fixture
def kms_credentials(tmp_path, monkeypatch):
    """仅替换 SDK 解密边界，文件读取及配置解析使用实际实现。"""
    envelope = tmp_path / "envelope"
    envelope.write_text("encrypted-envelope\n")
    monkeypatch.setenv(ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(ENVELOPE_PATH_ENV_VAR, str(envelope))
    monkeypatch.setenv(PRIVATE_KEY_ENV_VAR, "private-key")
    for var in ("DATABASE_URL", "BKKRILL_ENCRYPT_SECRET_KEY", "BKAUTH_TOKEN_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)
    # 明文为空是 chart 开启 KMS 后的实际配置。
    monkeypatch.setenv("MYSQL_PASSWORD", "")
    monkeypatch.setenv("PAAS_SERVICE_JWT_CLIENTS_KEY", "")
    decrypt = Mock(return_value=json.dumps(CREDENTIALS))
    monkeypatch.setattr("bk_kms.decrypt", decrypt)
    return decrypt


def test_disabled_does_not_read_envelope(kms_credentials, monkeypatch):
    monkeypatch.delenv(ENABLED_ENV_VAR)
    monkeypatch.setenv("PAAS_SAAS_KMS_ENABLED", "true")
    monkeypatch.setenv("MYSQL_PASSWORD", "plain-password")

    env = get_env(BINDINGS, DEBUG=(bool, False))

    assert type(env) is environ.Env
    assert env("MYSQL_PASSWORD") == "plain-password"
    assert env("DEBUG") is False
    kms_credentials.assert_not_called()


def test_missing_field_falls_back_without_logging_secret(kms_credentials, monkeypatch, caplog):
    kms_credentials.return_value = json.dumps({"mysql": {"svc_mysql": {"password": ""}}})
    monkeypatch.setenv("MYSQL_PASSWORD", "plain-password")

    with caplog.at_level(logging.WARNING):
        env = get_env(BINDINGS, sensitive_vars=BINDINGS, required_vars=["MYSQL_PASSWORD"])

    assert env("MYSQL_PASSWORD") == "plain-password"
    assert [record.args[0] for record in caplog.records] == ["MYSQL_PASSWORD"]
    assert "plain-password" not in caplog.text


def test_required_field_missing_after_plaintext_removed(kms_credentials):
    kms_credentials.return_value = json.dumps({"jwt": CREDENTIALS["jwt"]})

    with pytest.raises(ImproperlyConfigured, match=r"MYSQL_PASSWORD is required.*mysql\.svc_mysql\.password"):
        get_env(BINDINGS, required_vars=BINDINGS)


def test_database_url_unsupported(kms_credentials, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@db/svc")

    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        get_env(BINDINGS)


def test_missing_private_key(kms_credentials, monkeypatch):
    monkeypatch.delenv(PRIVATE_KEY_ENV_VAR)

    with pytest.raises(ImproperlyConfigured, match=PRIVATE_KEY_ENV_VAR):
        get_env(BINDINGS)


def test_decryption_failure_hides_secret(kms_credentials):
    kms_credentials.side_effect = ValueError(DB_PASSWORD)

    with pytest.raises(ImproperlyConfigured) as exc_info:
        get_env(BINDINGS)

    assert DB_PASSWORD not in str(exc_info.value)
    assert exc_info.value.__suppress_context__


def _load_settings(directory, package, credentials):
    """隔离 settings 导入，防止 Django/MySQL 补丁在测试进程内相互影响。"""
    code = """
import importlib
import json
import sys
from unittest.mock import patch

with patch("bk_kms.decrypt", return_value=sys.stdin.read()):
    settings = importlib.import_module(sys.argv[1] + ".settings")
print(json.dumps({
    "user": settings.DATABASES["default"]["USER"],
    "password": settings.DATABASES["default"]["PASSWORD"],
    "encryption_key": settings.BKKRILL_ENCRYPT_SECRET_KEY.decode(),
    "jwt_key": settings.PAAS_SERVICE_JWT_CLIENTS[0]["key"],
    "django_key": settings.SECRET_KEY,
    "app_code": getattr(settings, "BK_APP_CODE", None),
    "app_secret": getattr(settings, "BK_APP_SECRET", None),
    "bkauth_secret": getattr(settings, "BKAUTH_TOKEN_SECRET_KEY", None),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, package],
        cwd=Path(__file__).parents[2] / directory,
        env={
            **os.environ,
            "MYSQL_PASSWORD": "plain-password",
            "DJANGO_SETTINGS_MODULE": f"{package}.settings",
            "SENTRY_DSN": "",
        },
        input=json.dumps(credentials),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize(("directory", "package", "instance"), SERVICES)
def test_settings_use_envelope_values(kms_credentials, directory, package, instance):
    settings = _load_settings(directory, package, CREDENTIALS)

    assert settings["user"] == instance
    assert settings["password"] == DB_PASSWORD
    assert settings["encryption_key"] == ("otel-key" if package == "svc_otel" else "krill-key")
    assert settings["jwt_key"] == "jwt-client-key"
    if package == "svc_rabbitmq":
        assert settings["django_key"] == "rabbitmq-django-key"
    if package == "svc_otel":
        assert settings["app_code"] == "bk_paas3"
        assert settings["app_secret"] == settings["bkauth_secret"] == "$app-secret"


def test_otel_empty_encryption_key_preserves_default(kms_credentials):
    credentials = {**CREDENTIALS, "encryption": {"bk_krill_otel": {"secret_key": ""}}}

    settings = _load_settings("svc-otel", "svc_otel", credentials)

    assert settings["encryption_key"] == "b1ZPY1FDTXV1WGpGb0x2cmJKdlVLQW5OdnJBb2FscVY="
