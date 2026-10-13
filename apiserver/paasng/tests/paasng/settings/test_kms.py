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
import copy
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.core.exceptions import ImproperlyConfigured
from dynaconf import LazySettings
from kombu.utils.url import url_to_parts
from redis import ConnectionPool

from paasng.settings import kms
from paasng.settings.kms import (
    ENABLED_ENV_VAR,
    ENVELOPE_PATH_ENV_VAR,
    PRIVATE_KEY_PATH_ENV_VAR,
    KMSSettings,
    load_kms_settings,
    load_kms_workloads_settings,
)
from paasng.settings.utils import cache_from_redis_sentinel_url

# 包含 dynaconf 前缀等特殊字符，校验账号密码按原文使用
DB_PASSWORD = "@int p@ss:/w#rd?$HOME"
REDIS_PASSWORD = "r@dis:p$ss%zz"

CREDENTIALS: dict[str, Any] = {
    "env": {
        "PAAS_BK_APP_SECRET": "app-secret",
        "PAAS_BKKRILL_ENCRYPT_SECRET_KEY": "krill-key",
        "PAAS_HEALTHZ_TOKEN": "healthz-token",
        "PAAS_METRIC_CLIENT_TOKEN_DICT": "{bkmonitor='metric-token'}",
        "PAAS_PAAS_ANALYSIS_JWT_CONF": '@json {"algorithm": "HS256", "key": "jwt-key"}',
        "PAAS_WL_AGENT_SANDBOX_ROUTER_AUTH_TOKEN": "router-token",
    },
    "mysql": {
        "default": {"username": "paas", "password": DB_PASSWORD},
        "workloads": {"username": "wl", "password": "wl-password"},
    },
    "redis": {"default": {"password": REDIS_PASSWORD}},
    "bkrepo": {"default": {"username": "bkpaas3", "password": "bkrepo-password"}},
}

BASE_SETTINGS = {
    "DATABASE_NAME": "bk_paas3",
    "DATABASE_USER": "plain-user",
    "DATABASE_PASSWORD": "plain-password",
    "WL_DATABASE_NAME": "bk_paas3_engine",
    "REDIS_URL": "redis://:plain@redis.example.com:6379/0",
    "BLOBSTORE_BKREPO_CONFIG": {"PROJECT": "bkpaas", "ENDPOINT": "http://bkrepo", "USERNAME": "", "PASSWORD": ""},
    "BK_APP_SECRET": "plain-secret",
    "HEALTHZ_TOKEN": "plain-token",
    "BK_APP_CODE": "bk_paas3",
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
    """写入信封与私钥文件（内容末尾带换行，与 Secret 挂载一致），并开启平台 KMS"""

    def _write(credentials, envelope_key: rsa.RSAPrivateKey | None = None) -> dict[str, str]:
        envelope_path, private_key_path = tmp_path / "envelope", tmp_path / "privateKey"
        envelope_path.write_text(_make_envelope(envelope_key or private_key, json.dumps(credentials)) + "\n")
        private_key_path.write_text(_private_key_text(private_key) + "\n")
        env = {
            ENABLED_ENV_VAR: "true",
            ENVELOPE_PATH_ENV_VAR: str(envelope_path),
            PRIVATE_KEY_PATH_ENV_VAR: str(private_key_path),
        }
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        kms._decrypt_credentials.cache_clear()
        return env

    yield _write
    kms._decrypt_credentials.cache_clear()


def _make_settings(**values) -> LazySettings:
    settings = LazySettings(environments=False, ENVVAR_PREFIX_FOR_DYNACONF="PAAS_KMS_UNITTEST")
    for key, value in values.items():
        settings.set(key, value)
    return settings


def _load(credentials, write_kms_files, **values):
    write_kms_files(credentials)
    return load_kms_settings(_make_settings(**{**BASE_SETTINGS, **values}))


def _parse_redis_url(url: str) -> dict:
    return ConnectionPool.from_url(url).connection_kwargs


@pytest.mark.parametrize("value", [None, "false", "1", "TRUE", " true"])
def test_disabled(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(ENABLED_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(ENABLED_ENV_VAR, value)
    settings = _make_settings(**BASE_SETTINGS)
    assert load_kms_settings(settings) is settings
    assert load_kms_workloads_settings(settings) is settings


class TestEnvSection:
    def test_parsed_like_env_vars(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        assert settings.get("BK_APP_SECRET") == "app-secret"
        assert settings.get("BKKRILL_ENCRYPT_SECRET_KEY") == "krill-key"
        assert settings.get("HEALTHZ_TOKEN") == "healthz-token"
        assert settings.get("METRIC_CLIENT_TOKEN_DICT") == {"bkmonitor": "metric-token"}
        assert settings.get("PAAS_ANALYSIS_JWT_CONF") == {"algorithm": "HS256", "key": "jwt-key"}
        # 与环境变量一致，PAAS_WL_ 开头的变量对 apiserver 配置以 WL_ 开头生效
        assert settings.get("WL_AGENT_SANDBOX_ROUTER_AUTH_TOKEN") == "router-token"
        assert settings.get("BK_APP_CODE") == "bk_paas3"
        assert settings.get("NOT_EXISTS", "default") == "default"

    def test_workloads_settings(self, write_kms_files):
        write_kms_files(CREDENTIALS)
        settings = load_kms_workloads_settings(_make_settings(HEALTHZ_TOKEN="plain"))

        assert settings.get("AGENT_SANDBOX_ROUTER_AUTH_TOKEN") == "router-token"
        assert settings.get("HEALTHZ_TOKEN") == "plain"

    def test_account_section_wins(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["env"]["PAAS_DATABASE_PASSWORD"] = "from-env"
        assert _load(credentials, write_kms_files).get("DATABASE_PASSWORD") == DB_PASSWORD

    def test_bkkrill_is_required(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        del credentials["env"]["PAAS_BKKRILL_ENCRYPT_SECRET_KEY"]
        with pytest.raises(ImproperlyConfigured, match="BKKRILL_ENCRYPT_SECRET_KEY is required"):
            _load(credentials, write_kms_files)

    def test_unprefixed_name_is_ignored(self, write_kms_files, caplog):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["env"]["HEALTHZ_TOKEN"] = "wrong-name"
        with caplog.at_level(logging.WARNING):
            settings = _load(credentials, write_kms_files)

        assert settings.get("HEALTHZ_TOKEN") == "healthz-token"
        assert "KMS env HEALTHZ_TOKEN is ignored" in caplog.text


class TestAccountSections:
    def test_overrides(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        assert isinstance(settings, KMSSettings)
        assert settings.get("DATABASE_USER") == "paas"
        assert settings.get("DATABASE_PASSWORD") == DB_PASSWORD
        assert settings.get("WL_DATABASE_USER") == "wl"
        assert settings.get("BLOBSTORE_BKREPO_CONFIG") == {
            "PROJECT": "bkpaas",
            "ENDPOINT": "http://bkrepo",
            "USERNAME": "bkpaas3",
            "PASSWORD": "bkrepo-password",
        }

    def test_redis_url(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        parsed = _parse_redis_url(settings.get("REDIS_URL"))
        assert (parsed["password"], parsed["host"], parsed["port"], parsed["db"]) == (
            REDIS_PASSWORD,
            "redis.example.com",
            6379,
            0,
        )
        assert settings.get("CELERY_BROKER_URL") is None

    def test_sentinel_urls(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["redis"]["sentinel"] = {"password": "sentinel-password"}
        sentinel_url = "sentinel://:@s1.example.com:26379/0;sentinel://:@s2.example.com:26379/0"
        settings = _load(credentials, write_kms_files, REDIS_URL=sentinel_url, CELERY_BROKER_URL=sentinel_url)

        for key in ("REDIS_URL", "CELERY_BROKER_URL"):
            urls = settings.get(key).split(";")
            assert [url_to_parts(url).password for url in urls] == [REDIS_PASSWORD, REDIS_PASSWORD]
        assert settings.get("SENTINEL_PASSWORD") == "sentinel-password"
        assert settings.get("CELERY_BROKER_SENTINEL_PASSWORD") == "sentinel-password"

        cache = cache_from_redis_sentinel_url(settings.get("REDIS_URL"), "mymaster", "sentinel-password")
        assert cache["OPTIONS"]["PASSWORD"] == REDIS_PASSWORD

    def test_amqp_broker(self, write_kms_files):
        credentials = {**CREDENTIALS, "rabbitmq": {"default": {"username": "mq@user", "password": "mq@pass:1"}}}
        settings = _load(credentials, write_kms_files, CELERY_BROKER_URL="amqp://old:old@mq.example.com:5672/vhost")

        parts = url_to_parts(settings.get("CELERY_BROKER_URL"))
        assert (parts.username, parts.password, parts.hostname, parts.path) == (
            "mq@user",
            "mq@pass:1",
            "mq.example.com",
            "vhost",
        )

    @pytest.mark.parametrize(
        ("path", "value"),
        [
            (("mysql", "workloads", "password"), None),
            (("redis", "default", "password"), "  "),
            (("bkrepo", "default", "username"), 123),
        ],
    )
    def test_invalid_field_in_provided_section(self, write_kms_files, path, value):
        credentials = copy.deepcopy(CREDENTIALS)
        parent: Any = credentials
        for part in path[:-1]:
            parent = parent[part]
        if value is None:
            del parent[path[-1]]
        else:
            parent[path[-1]] = value

        with pytest.raises(ImproperlyConfigured, match=rf"KMS requires a non-empty string at {'.'.join(path)}"):
            _load(credentials, write_kms_files)

    @pytest.mark.parametrize("password", ["a/b", "a?b", "a#b", "a%41b"])
    def test_password_unsupported_in_url(self, write_kms_files, password):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["redis"]["default"]["password"] = password

        with pytest.raises(ImproperlyConfigured, match=r"redis\.default\.password contains characters unsupported"):
            _load(credentials, write_kms_files)

    def test_encrypted_database_url_is_rejected(self, write_kms_files, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "encrypted")
        with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
            _load(CREDENTIALS, write_kms_files)


class TestPlaintextFallback:
    def test_missing_sections_use_plaintext_with_warning(self, write_kms_files, caplog):
        credentials = {"env": {"PAAS_BKKRILL_ENCRYPT_SECRET_KEY": "krill-key"}}
        with caplog.at_level(logging.WARNING):
            settings = _load(
                credentials,
                write_kms_files,
                BLOBSTORE_BKREPO_CONFIG={"PROJECT": "bkpaas", "PASSWORD": "plain"},
            )

        assert settings.get("DATABASE_PASSWORD") == "plain-password"
        assert settings.get("REDIS_URL") == BASE_SETTINGS["REDIS_URL"]
        assert settings.get("BK_APP_SECRET") == "plain-secret"
        for key in ("DATABASE_PASSWORD", "REDIS_URL", "BLOBSTORE_BKREPO_CONFIG", "BK_APP_SECRET", "HEALTHZ_TOKEN"):
            assert f"Sensitive setting {key} is not provided by KMS" in caplog.text
        assert "plain-password" not in caplog.text

    def test_no_warning_when_provided(self, write_kms_files, caplog):
        with caplog.at_level(logging.WARNING):
            _load(CREDENTIALS, write_kms_files)
        assert "Sensitive setting" not in caplog.text

    @pytest.mark.parametrize(
        ("hosts", "warned"),
        [
            ("[{host='es.example.com', port='9200', http_auth='elastic:pwd'}]", True),
            ("[{host='es.example.com', port='9200'}]", False),
        ],
    )
    def test_elasticsearch_hosts(self, write_kms_files, caplog, monkeypatch, hosts, warned):
        monkeypatch.setenv("PAAS_KMS_UNITTEST_ELASTICSEARCH_HOSTS", hosts)
        with caplog.at_level(logging.WARNING):
            _load(CREDENTIALS, write_kms_files)
        assert ("Sensitive setting ELASTICSEARCH_HOSTS" in caplog.text) is warned

    def test_elasticsearch_hosts_from_envelope(self, write_kms_files, caplog):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["env"]["PAAS_ELASTICSEARCH_HOSTS"] = (
            "[{host='es.example.com', port='9200', http_auth='elastic:pwd'}]"
        )
        with caplog.at_level(logging.WARNING):
            settings = _load(credentials, write_kms_files)

        assert settings.get("ELASTICSEARCH_HOSTS") == [
            {"host": "es.example.com", "port": "9200", "http_auth": "elastic:pwd"}
        ]
        assert "ELASTICSEARCH_HOSTS" not in caplog.text

    def test_no_warning_without_password(self, write_kms_files, caplog):
        credentials = copy.deepcopy(CREDENTIALS)
        del credentials["redis"]
        with caplog.at_level(logging.WARNING):
            settings = _load(credentials, write_kms_files, REDIS_URL="redis://redis.example.com:6379/0")

        assert settings.get("REDIS_URL") == "redis://redis.example.com:6379/0"
        assert "REDIS_URL" not in caplog.text


class TestDecryptFailure:
    def test_wrong_private_key(self, write_kms_files):
        write_kms_files(CREDENTIALS, envelope_key=rsa.generate_private_key(public_exponent=65537, key_size=2048))

        with pytest.raises(ImproperlyConfigured, match="Unable to read or decrypt") as exc_info:
            load_kms_settings(_make_settings(**BASE_SETTINGS))
        assert exc_info.value.__cause__ is None

    def test_missing_envelope_file(self, write_kms_files, monkeypatch, tmp_path):
        write_kms_files(CREDENTIALS)
        monkeypatch.setenv(ENVELOPE_PATH_ENV_VAR, str(tmp_path / "not-exists"))

        with pytest.raises(ImproperlyConfigured, match="Unable to read or decrypt"):
            load_kms_settings(_make_settings(**BASE_SETTINGS))


def test_settings_module_in_new_process(write_kms_files):
    """在独立进程中按 KMS 模式加载完整的 paasng.settings，验证早期加载顺序与派生配置"""
    # 本地 settings_local.yaml 可能配置了其他数据库实例，信封中一并提供
    credentials = copy.deepcopy(CREDENTIALS)
    for instance in ("legacy", "console"):
        credentials["mysql"][instance] = {"username": instance, "password": f"{instance}-password"}
    kms_env = write_kms_files(credentials)
    # 原配置中不提供 BKKRILL_ENCRYPT_SECRET_KEY，KMS 模式下不再要求它
    env = {k: v for k, v in os.environ.items() if not k.startswith("PAAS_")}
    env.update(
        kms_env,
        PAAS_DATABASE_NAME="bk_paas3",
        PAAS_DATABASE_PASSWORD="plain-password",
        PAAS_REDIS_URL="redis://:@redis.example.com:6379/0",
        PAAS_CELERY_BROKER_URL="redis://:@redis.example.com:6379/1",
        PAAS_BLOBSTORE_BKREPO_CONFIG='@json {"PROJECT": "bkpaas", "ENDPOINT": "http://bkrepo"}',
    )
    env.pop("DJANGO_SETTINGS_MODULE", None)
    script = (
        "import json, paasng.settings as s;"
        "print(json.dumps({"
        "'db': [s.DATABASES['default']['USER'], s.DATABASES['default']['PASSWORD']],"
        "'krill': s.BKKRILL_ENCRYPT_SECRET_KEY.decode(), 'iam_secret': s.IAM_APP_SECRET,"
        "'healthz': s.HEALTHZ_TOKEN, 'metric': s.METRIC_CLIENT_TOKEN_DICT,"
        "'router': s.AGENT_SANDBOX_ROUTER_AUTH_TOKEN,"
        "'cache': s.CACHES['default']['LOCATION'], 'broker': s.CELERY_BROKER_URL,"
        "'bkrepo': s.BLOBSTORE_BKREPO_CONFIG['PASSWORD']}))"
    )
    paasng_dir = Path(__file__).parents[3]
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=paasng_dir, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr[-2000:]

    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["db"] == ["paas", DB_PASSWORD]
    assert data["krill"] == "krill-key"
    # 默认取 BK_APP_SECRET 的派生配置使用解密后的值
    assert data["iam_secret"] == "app-secret"
    assert data["healthz"] == "healthz-token"
    assert data["metric"] == {"bkmonitor": "metric-token"}
    assert data["router"] == "router-token"
    assert _parse_redis_url(data["cache"])["password"] == REDIS_PASSWORD
    assert _parse_redis_url(data["broker"])["password"] == REDIS_PASSWORD
    assert data["bkrepo"] == "bkrepo-password"
