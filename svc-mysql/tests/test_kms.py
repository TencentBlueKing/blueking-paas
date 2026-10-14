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

import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import environ
import pytest
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.core.exceptions import ImproperlyConfigured
from svc_mysql.settings.kms import (
    ENABLED_ENV_VAR,
    ENVELOPE_PATH_ENV_VAR,
    PRIVATE_KEY_ENV_VAR,
    KMSEnv,
    get_env,
)

# 包含 "$" 开头等特殊字符，校验信封中的值按原文使用
DB_PASSWORD = "$HOME p@ss:/w#rd?"

# 与运维的凭证字段结构一致，包含 svc-mysql 不读取的字段
CREDENTIALS = {
    "mysql": {
        "svc_mysql": {"username": "svc", "password": DB_PASSWORD},
        "saas_plan": {"username": "root", "password": "plan-password"},
    },
    "encryption": {"bk_krill": {"secret_key": "a3JpbGwta2V5LWZvci10ZXN0aW5nLW9ubHktMzJieXQ="}},
    "jwt": {"services": {"client_key": "jwt-client-key"}},
}

BINDINGS = {
    "MYSQL_USER": "mysql.svc_mysql.username",
    "MYSQL_PASSWORD": "mysql.svc_mysql.password",
    "BKKRILL_ENCRYPT_SECRET_KEY": "encryption.bk_krill.secret_key",
    "PAAS_SERVICE_JWT_CLIENTS_KEY": "jwt.services.client_key",
}


@pytest.fixture(scope="module")
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _make_envelope(private_key: rsa.RSAPrivateKey, plaintext: str) -> str:
    """按 KMS 信封格式加密：RSA-OAEP(SHA-256) 加密数据密钥，AES-CBC 加密 IV || 密文"""
    data_key, iv = os.urandom(16), os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(data_key), modes.CBC(iv)).encryptor()
    ciphertext = iv + encryptor.update(padded) + encryptor.finalize()
    oaep = asym_padding.OAEP(mgf=asym_padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    payload = {
        "asymmetric_type": "RSA",
        "symmetric_type": "AES",
        "symmetric_mode": "CBC",
        "encrypted_key": _b64(private_key.public_key().encrypt(data_key, oaep)),
        "ciphertext": _b64(ciphertext),
    }
    return _b64(json.dumps(payload).encode())


def _private_key_text(private_key: rsa.RSAPrivateKey) -> str:
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return _b64(pem)


@pytest.fixture
def write_kms_files(tmp_path, private_key, monkeypatch):
    """写入信封文件（内容末尾带换行，与 Secret 挂载一致），设置私钥环境变量并开启 KMS"""
    envelope_path = tmp_path / "envelope"
    monkeypatch.setenv(ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(ENVELOPE_PATH_ENV_VAR, str(envelope_path))
    monkeypatch.setenv(PRIVATE_KEY_ENV_VAR, _private_key_text(private_key))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for var in BINDINGS:
        monkeypatch.delenv(var, raising=False)

    def write(credentials) -> Path:
        envelope_path.write_text(_make_envelope(private_key, json.dumps(credentials)) + "\n")
        return envelope_path

    return write


@pytest.mark.parametrize("value", [None, "", "1", "TRUE", "yes"])
def test_disabled(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(ENABLED_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENABLED_ENV_VAR, value)

    env = get_env(BINDINGS, DEBUG=(bool, False))

    assert type(env) is environ.Env
    assert env("DEBUG") is False


def test_values_from_envelope(write_kms_files, monkeypatch):
    write_kms_files(CREDENTIALS)
    monkeypatch.setenv("MYSQL_PASSWORD", "plain-password")
    monkeypatch.setenv("MYSQL_HOST", "db.example.com")

    env = get_env(BINDINGS)

    assert isinstance(env, KMSEnv)
    assert env("MYSQL_USER", default="svc_mysql") == "svc"
    assert env("MYSQL_PASSWORD", default="blueking") == DB_PASSWORD
    assert env.str("PAAS_SERVICE_JWT_CLIENTS_KEY") == "jwt-client-key"
    assert env.bytes("BKKRILL_ENCRYPT_SECRET_KEY") == CREDENTIALS["encryption"]["bk_krill"]["secret_key"].encode()
    assert env("MYSQL_HOST", default="127.0.0.1") == "db.example.com"


def test_missing_field_falls_back_to_env_var(write_kms_files, monkeypatch, caplog):
    write_kms_files({"mysql": {"svc_mysql": {"username": "svc", "password": ""}}, "jwt": {}})
    monkeypatch.setenv("MYSQL_PASSWORD", "plain-password")
    monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.example.com/1")

    with caplog.at_level(logging.WARNING):
        env = get_env(BINDINGS, sensitive_vars=["MYSQL_PASSWORD", "PAAS_SERVICE_JWT_CLIENTS_KEY", "SENTRY_DSN"])

    assert env("MYSQL_PASSWORD") == "plain-password"
    assert env("MYSQL_USER") == "svc"
    warned = {record.args[0] for record in caplog.records}
    assert warned == {"MYSQL_PASSWORD", "SENTRY_DSN"}
    assert "plain-password" not in caplog.text


def test_required_var(write_kms_files, monkeypatch):
    write_kms_files({"mysql": CREDENTIALS["mysql"]})

    with pytest.raises(ImproperlyConfigured, match="BKKRILL_ENCRYPT_SECRET_KEY is required"):
        get_env(BINDINGS, required_vars=["BKKRILL_ENCRYPT_SECRET_KEY"])

    monkeypatch.setenv("BKKRILL_ENCRYPT_SECRET_KEY", "plain-key")
    assert get_env(BINDINGS, required_vars=["BKKRILL_ENCRYPT_SECRET_KEY"]).str("BKKRILL_ENCRYPT_SECRET_KEY") == (
        "plain-key"
    )


def test_required_var_cleared_by_chart(write_kms_files, monkeypatch):
    """开启 KMS 后 chart 把明文置为空字符串，信封也未提供时阻止启动，并提示缺少的信封字段"""
    write_kms_files({"jwt": CREDENTIALS["jwt"]})
    monkeypatch.setenv("MYSQL_PASSWORD", "")

    with pytest.raises(
        ImproperlyConfigured,
        match=r"MYSQL_PASSWORD is required, provide it by KMS credential mysql\.svc_mysql\.password",
    ):
        get_env(BINDINGS, required_vars=["MYSQL_PASSWORD", "PAAS_SERVICE_JWT_CLIENTS_KEY"])


def test_database_url_unsupported(write_kms_files, monkeypatch):
    write_kms_files(CREDENTIALS)
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@db/svc")

    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        get_env(BINDINGS)


def test_non_string_field(write_kms_files):
    write_kms_files({"mysql": {"svc_mysql": {"password": 123}}})

    with pytest.raises(ImproperlyConfigured, match=r"mysql\.svc_mysql\.password"):
        get_env(BINDINGS)


def test_missing_private_key(write_kms_files, monkeypatch):
    write_kms_files(CREDENTIALS)
    monkeypatch.delenv(PRIVATE_KEY_ENV_VAR)

    with pytest.raises(ImproperlyConfigured, match=PRIVATE_KEY_ENV_VAR):
        get_env(BINDINGS)


def test_invalid_envelope_hides_content(write_kms_files):
    path = write_kms_files(CREDENTIALS)
    path.write_text("not-an-envelope-" + DB_PASSWORD)

    with pytest.raises(ImproperlyConfigured) as exc_info:
        get_env(BINDINGS)

    assert DB_PASSWORD not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_non_object_envelope(write_kms_files):
    write_kms_files(["not", "an", "object"])

    with pytest.raises(ImproperlyConfigured, match="JSON object"):
        get_env(BINDINGS)


def test_settings_module_in_new_process(write_kms_files):
    """在新进程中加载 settings，校验各配置项实际取到信封中的值"""
    write_kms_files(CREDENTIALS)
    env = {**os.environ, "MYSQL_PASSWORD": "plain-password", "BKKRILL_ENCRYPT_SECRET_KEY": "plain-key"}
    code = (
        "import json, svc_mysql.settings as s;"
        "print(json.dumps([s.DATABASES['default']['USER'], s.DATABASES['default']['PASSWORD'],"
        " s.BKKRILL_ENCRYPT_SECRET_KEY.decode(), s.PAAS_SERVICE_JWT_CLIENTS[0]['key']]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout) == [
        "svc",
        DB_PASSWORD,
        CREDENTIALS["encryption"]["bk_krill"]["secret_key"],
        "jwt-client-key",
    ]
