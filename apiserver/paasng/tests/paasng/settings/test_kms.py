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
    PRIVATE_KEY_ENV_VAR,
    KMSSettings,
    get_kms_credential,
    load_kms_settings,
    load_kms_workloads_settings,
)
from paasng.settings.utils import cache_from_redis_sentinel_url

# 包含 dynaconf 前缀等特殊字符，校验账号密码按原文使用
DB_PASSWORD = "@int p@ss:/w#rd?$HOME"
REDIS_PASSWORD = "r@dis:p$ss%zz"
BROKER_URL = "amqp://mq:p%40ss@mq.example.com:5672/vhost"

# 与运维的 bk_paas_runtime_config 一致，包含 apiserver 不读取的字段
CREDENTIALS: dict[str, Any] = {
    "bkapp_id_secret": {"default": {"app_code": "bk_paas3", "app_secret": "app-secret"}},
    "mysql": {
        "apiserver": {"username": "paas", "password": DB_PASSWORD},
        "workloads": {"username": "wl", "password": "wl-password"},
        "svc_mysql": {"username": "svc", "password": "svc-password"},
        "admin": {"password": "root-password"},
    },
    "redis": {"default": {"password": REDIS_PASSWORD}, "sentinel": {"password": ""}},
    "celery": {"default": {"uri": BROKER_URL}},
    "rabbitmq": {"default": {"username": "admin", "password": "mq-admin"}, "cluster": {"erlang_cookie": "cookie"}},
    "bkrepo": {"default": {"username": "bkpaas3", "password": "bkrepo-password"}},
    "registry": {"external": {"username": "", "password": ""}, "image_pull": {"secret_names": ["pull-secret"]}},
    "jwt": {"services": {"client_key": "jwt-client-key"}, "paas_analysis": {"key": "analysis-key"}},
    "encryption": {"bk_krill": {"secret_key": "krill-key"}, "slug": {"secret_key": "slug-key"}},
    "tokens": {
        "healthz": {"token": "healthz-token"},
        "metrics": {"token": "metric-token"},
        "agent_sandbox_daemon": {"token": "daemon-token"},
        "agent_sandbox_router": {"token": "router-token"},
    },
    "telemetry": {"default": {"token": "otel-token"}},
    "sentry": {"default": {"dsn": "https://key@sentry.example.com/1"}},
    "elasticsearch": {"default": {"hosts": "[{host='es.example.com', port='9200', http_auth='elastic:pwd'}]"}},
}

BASE_SETTINGS = {
    "DATABASE_NAME": "bk_paas3",
    "DATABASE_USER": "plain-user",
    "DATABASE_PASSWORD": "plain-password",
    "WL_DATABASE_NAME": "bk_paas3_engine",
    "REDIS_URL": "redis://:plain@redis.example.com:6379/0",
    "CELERY_BROKER_URL": "amqp://mq:plain@mq.example.com:5672/vhost",
    "BLOBSTORE_BKREPO_CONFIG": {"PROJECT": "bkpaas", "ENDPOINT": "http://bkrepo", "USERNAME": "", "PASSWORD": ""},
    "SMART_DOCKER_USERNAME": "bkpaas3",
    "SMART_DOCKER_PASSWORD": "plain-docker",
    "APP_DOCKER_USERNAME": "bkpaas3",
    "APP_DOCKER_PASSWORD": "plain-docker",
    "BK_APP_SECRET": "plain-secret",
    "HEALTHZ_TOKEN": "plain-token",
    "METRIC_CLIENT_TOKEN_DICT": {"bkmonitor": "plain-metric", "other": "other-token"},
    "SENTRY_CONFIG": {"dsn": "https://plain@sentry.example.com/1", "environment": "prod"},
    "PAAS_ANALYSIS_JWT_CONF": {"algorithm": "HS256", "iss": "paas", "key": "plain-key"},
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

    def _write(credentials, envelope_key: rsa.RSAPrivateKey | None = None) -> dict[str, str]:
        envelope_path = tmp_path / "bk-paas-kms"
        envelope_path.write_text(_make_envelope(envelope_key or private_key, json.dumps(credentials)) + "\n")
        env = {
            ENABLED_ENV_VAR: "true",
            ENVELOPE_PATH_ENV_VAR: str(envelope_path),
            PRIVATE_KEY_ENV_VAR: _private_key_text(private_key),
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


def _without(credentials, *paths: str) -> dict:
    """返回删除了指定字段的信封"""
    result = copy.deepcopy(credentials)
    for path in paths:
        *parents, name = path.split(".")
        node = result
        for part in parents:
            node = node[part]
        del node[name]
    return result


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
    assert get_kms_credential("tokens.healthz.token") is None


class TestOverrides:
    def test_simple_fields(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        assert isinstance(settings, KMSSettings)
        assert settings.get("BK_APP_CODE") == "bk_paas3"
        assert settings.get("BK_APP_SECRET") == "app-secret"
        assert settings.get("BKKRILL_ENCRYPT_SECRET_KEY") == "krill-key"
        assert settings.get("SLUG_ENCRYPT_SECRET_KEY") == "slug-key"
        assert settings.get("ONE_SIMPLE_JWT_AUTH_KEY") == "jwt-client-key"
        assert settings.get("HEALTHZ_TOKEN") == "healthz-token"
        assert settings.get("AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN") == "daemon-token"
        assert settings.get("OTEL_BK_DATA_TOKEN") == "otel-token"
        assert settings.get("CELERY_BROKER_URL") == BROKER_URL
        assert settings.get("NOT_EXISTS", "default") == "default"

    def test_fields_merged_into_dict_settings(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        assert settings.get("METRIC_CLIENT_TOKEN_DICT") == {"bkmonitor": "metric-token", "other": "other-token"}
        assert settings.get("SENTRY_CONFIG") == {"dsn": "https://key@sentry.example.com/1", "environment": "prod"}
        assert settings.get("PAAS_ANALYSIS_JWT_CONF") == {"algorithm": "HS256", "iss": "paas", "key": "analysis-key"}

    @pytest.mark.parametrize(
        "hosts",
        [
            "[{host='es.example.com', port='9200', http_auth='elastic:pwd'}]",
            '@json [{"host": "es.example.com", "port": "9200", "http_auth": "elastic:pwd"}]',
        ],
    )
    def test_elasticsearch_hosts_parsed_like_env_var(self, write_kms_files, hosts):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["elasticsearch"]["default"]["hosts"] = hosts

        assert _load(credentials, write_kms_files).get("ELASTICSEARCH_HOSTS") == [
            {"host": "es.example.com", "port": "9200", "http_auth": "elastic:pwd"}
        ]

    def test_workloads_settings(self, write_kms_files):
        write_kms_files(CREDENTIALS)
        settings = load_kms_workloads_settings(_make_settings(HEALTHZ_TOKEN="plain"))

        assert settings.get("AGENT_SANDBOX_ROUTER_AUTH_TOKEN") == "router-token"
        assert settings.get("HEALTHZ_TOKEN") == "plain"

    @pytest.mark.parametrize(
        ("missing_path", "key"),
        [
            ("encryption.bk_krill", "BKKRILL_ENCRYPT_SECRET_KEY"),
            ("encryption.slug", "SLUG_ENCRYPT_SECRET_KEY"),
        ],
    )
    def test_required_keys(self, write_kms_files, missing_path, key):
        with pytest.raises(ImproperlyConfigured, match=f"{key} is required"):
            _load(_without(CREDENTIALS, missing_path), write_kms_files)

    def test_non_string_field(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["tokens"]["healthz"]["token"] = 123
        with pytest.raises(ImproperlyConfigured, match=r"KMS requires a string at tokens\.healthz\.token"):
            _load(credentials, write_kms_files)


class TestAccounts:
    def test_databases(self, write_kms_files):
        settings = _load(
            CREDENTIALS,
            write_kms_files,
            BK_CONSOLE_DATABASE_NAME="open_paas",
            BK_CONSOLE_DATABASE_USER="plain-user",
        )

        assert (settings.get("DATABASE_USER"), settings.get("DATABASE_PASSWORD")) == ("paas", DB_PASSWORD)
        assert (settings.get("WL_DATABASE_USER"), settings.get("WL_DATABASE_PASSWORD")) == ("wl", "wl-password")
        # 信封中没有 mysql.open_paas，保持原配置
        assert settings.get("BK_CONSOLE_DATABASE_USER") == "plain-user"

    def test_open_paas_database(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["mysql"]["open_paas"] = {"username": "open", "password": "open-password"}
        settings = _load(credentials, write_kms_files, BK_CONSOLE_DATABASE_NAME="open_paas")

        assert settings.get("BK_CONSOLE_DATABASE_USER") == "open"
        assert settings.get("BK_CONSOLE_DATABASE_PASSWORD") == "open-password"

    def test_database_username_kept_when_empty(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["mysql"]["apiserver"]["username"] = ""
        settings = _load(credentials, write_kms_files)

        assert (settings.get("DATABASE_USER"), settings.get("DATABASE_PASSWORD")) == ("plain-user", DB_PASSWORD)

    def test_bkrepo(self, write_kms_files):
        assert _load(CREDENTIALS, write_kms_files).get("BLOBSTORE_BKREPO_CONFIG") == {
            "PROJECT": "bkpaas",
            "ENDPOINT": "http://bkrepo",
            "USERNAME": "bkpaas3",
            "PASSWORD": "bkrepo-password",
        }

    def test_docker_registry_uses_bkrepo_account(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        assert settings.get("SMART_DOCKER_PASSWORD") == "bkrepo-password"
        assert settings.get("APP_DOCKER_PASSWORD") == "bkrepo-password"

    def test_docker_registry_uses_external_account(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["registry"]["external"] = {"username": "ext-user", "password": "ext-password"}
        settings = _load(
            credentials, write_kms_files, SMART_DOCKER_USERNAME="ext-user", APP_DOCKER_USERNAME="ext-user"
        )

        assert settings.get("SMART_DOCKER_PASSWORD") == "ext-password"
        assert settings.get("APP_DOCKER_PASSWORD") == "ext-password"

    def test_redis_url(self, write_kms_files):
        settings = _load(CREDENTIALS, write_kms_files)

        parsed = _parse_redis_url(settings.get("REDIS_URL"))
        assert (parsed["password"], parsed["host"], parsed["port"], parsed["db"]) == (
            REDIS_PASSWORD,
            "redis.example.com",
            6379,
            0,
        )

    def test_redis_broker_without_celery_uri(self, write_kms_files):
        settings = _load(
            _without(CREDENTIALS, "celery"), write_kms_files, CELERY_BROKER_URL="redis://:@redis.example.com:6379/1"
        )

        assert _parse_redis_url(settings.get("CELERY_BROKER_URL"))["password"] == REDIS_PASSWORD

    def test_sentinel_urls(self, write_kms_files):
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["redis"]["sentinel"] = {"password": "sentinel-password"}
        sentinel_url = "sentinel://:@s1.example.com:26379/0;sentinel://:@s2.example.com:26379/0"
        settings = _load(credentials, write_kms_files, REDIS_URL=sentinel_url)

        urls = settings.get("REDIS_URL").split(";")
        assert [url_to_parts(url).password for url in urls] == [REDIS_PASSWORD, REDIS_PASSWORD]
        assert settings.get("SENTINEL_PASSWORD") == "sentinel-password"
        assert settings.get("CELERY_BROKER_SENTINEL_PASSWORD") == "sentinel-password"

        cache = cache_from_redis_sentinel_url(settings.get("REDIS_URL"), "mymaster", "sentinel-password")
        assert cache["OPTIONS"]["PASSWORD"] == REDIS_PASSWORD

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
    def test_no_warning_when_provided(self, write_kms_files, caplog):
        with caplog.at_level(logging.WARNING):
            _load(CREDENTIALS, write_kms_files)
        assert "Sensitive setting" not in caplog.text

    def test_missing_fields_use_plaintext_with_warning(self, write_kms_files, caplog):
        credentials = {"encryption": {"bk_krill": {"secret_key": "krill-key"}, "slug": {"secret_key": "slug-key"}}}
        with caplog.at_level(logging.WARNING):
            settings = _load(
                credentials,
                write_kms_files,
                BLOBSTORE_BKREPO_CONFIG={"PROJECT": "bkpaas", "PASSWORD": "plain"},
            )

        assert settings.get("DATABASE_PASSWORD") == "plain-password"
        assert settings.get("REDIS_URL") == BASE_SETTINGS["REDIS_URL"]
        assert settings.get("BK_APP_SECRET") == "plain-secret"
        for key in (
            "DATABASE_PASSWORD",
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "BLOBSTORE_BKREPO_CONFIG",
            "SMART_DOCKER_PASSWORD",
            "BK_APP_SECRET",
            "HEALTHZ_TOKEN",
            "METRIC_CLIENT_TOKEN_DICT",
            "SENTRY_CONFIG",
        ):
            assert f"Sensitive setting {key} is not provided by KMS" in caplog.text
        assert "plain-password" not in caplog.text

    def test_empty_fields_are_not_provided(self, write_kms_files, caplog):
        """运维的凭证声明会把未使用的字段渲染为空字符串"""
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["tokens"]["healthz"]["token"] = ""
        credentials["mysql"]["apiserver"]["password"] = "  "
        with caplog.at_level(logging.WARNING):
            settings = _load(credentials, write_kms_files)

        assert settings.get("HEALTHZ_TOKEN") == "plain-token"
        assert settings.get("DATABASE_PASSWORD") == "plain-password"
        assert "Sensitive setting HEALTHZ_TOKEN is not provided by KMS" in caplog.text
        assert "Sensitive setting DATABASE_PASSWORD is not provided by KMS" in caplog.text

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("ELASTICSEARCH_HOSTS", "[{host='es.example.com', port='9200'}]"),
            ("SENTRY_CONFIG", "{dsn=''}"),
            ("METRIC_CLIENT_TOKEN_DICT", "{}"),
        ],
    )
    def test_no_warning_without_credential(self, write_kms_files, caplog, monkeypatch, key, value):
        credentials = _without(CREDENTIALS, "elasticsearch", "sentry", "tokens.metrics")
        monkeypatch.setenv(f"PAAS_KMS_UNITTEST_{key}", value)
        with caplog.at_level(logging.WARNING):
            _load(credentials, write_kms_files, SENTRY_CONFIG={}, METRIC_CLIENT_TOKEN_DICT={})
        assert "Sensitive setting" not in caplog.text

    def test_no_warning_without_password(self, write_kms_files, caplog):
        with caplog.at_level(logging.WARNING):
            settings = _load(
                _without(CREDENTIALS, "redis"), write_kms_files, REDIS_URL="redis://redis.example.com:6379/0"
            )

        assert settings.get("REDIS_URL") == "redis://redis.example.com:6379/0"
        assert "REDIS_URL" not in caplog.text


class TestDecryptFailure:
    def test_wrong_private_key(self, write_kms_files):
        write_kms_files(CREDENTIALS, envelope_key=rsa.generate_private_key(public_exponent=65537, key_size=2048))

        with pytest.raises(ImproperlyConfigured, match="Unable to read or decrypt") as exc_info:
            load_kms_settings(_make_settings(**BASE_SETTINGS))
        assert exc_info.value.__cause__ is None

    def test_missing_private_key(self, write_kms_files, monkeypatch):
        write_kms_files(CREDENTIALS)
        monkeypatch.delenv(PRIVATE_KEY_ENV_VAR)

        with pytest.raises(ImproperlyConfigured, match=f"KMS requires {PRIVATE_KEY_ENV_VAR}"):
            load_kms_settings(_make_settings(**BASE_SETTINGS))

    def test_missing_envelope_file(self, write_kms_files, monkeypatch, tmp_path):
        write_kms_files(CREDENTIALS)
        monkeypatch.setenv(ENVELOPE_PATH_ENV_VAR, str(tmp_path / "not-exists"))

        with pytest.raises(ImproperlyConfigured, match="Unable to read or decrypt"):
            load_kms_settings(_make_settings(**BASE_SETTINGS))


def test_settings_module_in_new_process(write_kms_files):
    """在独立进程中按 KMS 模式加载完整的 paasng.settings，验证早期加载顺序与派生配置"""
    # 本地 settings_local.yaml 可能配置了其他数据库实例，信封中一并提供
    credentials = copy.deepcopy(CREDENTIALS)
    credentials["mysql"]["open_paas"] = {"username": "open", "password": "open-password"}
    kms_env = write_kms_files(credentials)
    # 原配置中不提供 BKKRILL_ENCRYPT_SECRET_KEY，KMS 模式下不再要求它
    env = {k: v for k, v in os.environ.items() if not k.startswith("PAAS_")}
    env.update(
        kms_env,
        PAAS_DATABASE_NAME="bk_paas3",
        PAAS_DATABASE_PASSWORD="plain-password",
        PAAS_REDIS_URL="redis://:@redis.example.com:6379/0",
        PAAS_CELERY_BROKER_URL="amqp://mq:@mq.example.com:5672/vhost",
        PAAS_BLOBSTORE_BKREPO_CONFIG='@json {"PROJECT": "bkpaas", "ENDPOINT": "http://bkrepo"}',
    )
    env.pop("DJANGO_SETTINGS_MODULE", None)
    script = (
        "import json, paasng.settings as s;"
        "print(json.dumps({"
        "'db': [s.DATABASES['default']['USER'], s.DATABASES['default']['PASSWORD']],"
        "'krill': s.BKKRILL_ENCRYPT_SECRET_KEY.decode(), 'iam_secret': s.IAM_APP_SECRET,"
        "'healthz': s.HEALTHZ_TOKEN, 'metric': s.METRIC_CLIENT_TOKEN_DICT,"
        "'router': s.AGENT_SANDBOX_ROUTER_AUTH_TOKEN, 'es': s.ELASTICSEARCH_HOSTS,"
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
    assert data["es"] == [{"host": "es.example.com", "port": "9200", "http_auth": "elastic:pwd"}]
    assert _parse_redis_url(data["cache"])["password"] == REDIS_PASSWORD
    assert data["broker"] == BROKER_URL
    assert data["bkrepo"] == "bkrepo-password"


class TestManagementCommands:
    def test_initial_default_cluster_reads_from_kms(self, write_kms_files, monkeypatch):
        from paas_wl.infras.cluster.management.commands.initial_default_cluster import Command, EnvVarKey

        credentials = copy.deepcopy(CREDENTIALS)
        credentials["kubernetes"] = {
            "default": {"ca_data": "kms-ca", "cert_data": "kms-cert", "key_data": "kms-key", "token": "kms-token"}
        }
        write_kms_files(credentials)
        monkeypatch.setenv(EnvVarKey.SUB_PATH_DOMAIN, "apps.example.com")
        monkeypatch.setenv(EnvVarKey.API_SERVER_URLS, '["https://k8s.example.com:6443"]')
        for key in (EnvVarKey.CA, EnvVarKey.CERT, EnvVarKey.KEY, EnvVarKey.TOKEN):
            monkeypatch.setenv(key, "")

        data = Command()._build_cluster_data()
        assert (data.ca_data, data.cert_data, data.key_data, data.token_value) == (
            "kms-ca",
            "kms-cert",
            "kms-key",
            "kms-token",
        )

    def test_init_bkrepo_reads_passwords_from_kms(self, write_kms_files, monkeypatch):
        from django.conf import settings as django_settings
        from django.core.management import call_command

        from paasng.plat_admin.initialization.management.commands import init_bkrepo

        monkeypatch.setattr(
            django_settings,
            "BLOBSTORE_BKREPO_CONFIG",
            {"PROJECT": "bkpaas", "ENDPOINT": "http://bkrepo"},
            raising=False,
        )
        credentials = copy.deepcopy(CREDENTIALS)
        credentials["bkrepo"] = {
            "admin": {"username": "admin", "password": "kms-super-pwd"},
            "default": {"username": "bkpaas3", "password": "kms-bkpaas3-pwd"},
            "addons": {"username": "addons", "password": "kms-addons-pwd"},
            "lesscode": {"username": "lesscode", "password": "kms-lesscode-pwd"},
        }
        write_kms_files(credentials)

        calls: list[tuple] = []

        class FakeManager:
            def __init__(self, username, password):
                calls.append(("manager", username, password))

            def create_project(self, name):
                calls.append(("project", name))

            def create_user_to_project(self, username, password, association_users, project):
                calls.append(("user_project", username, password, project))

            def create_repo(self, project, repo, repo_type, public):
                pass

            def create_user_to_repo(self, username, password, association_users, project, repo):
                calls.append(("user_repo", username, password, project, repo))

        monkeypatch.setattr(init_bkrepo.Command, "get_manager", staticmethod(FakeManager))

        # 命令行不传任何密码参数
        call_command(
            "init_bkrepo",
            "--dry-run=false",
            "--init-enabled=true",
            "--super-username=admin",
            "--bkpaas3-username=bkpaas3",
            "--addons-username=addons",
            "--lesscode-username=lesscode",
        )
        assert ("manager", "admin", "kms-super-pwd") in calls
        assert ("user_project", "bkpaas3", "kms-bkpaas3-pwd", "bkpaas") in calls
        assert ("user_project", "addons", "kms-addons-pwd", "bksaas-addons") in calls
        assert (
            "user_repo",
            "lesscode",
            "kms-lesscode-pwd",
            "bkpaas",
            "npm",
        ) in calls

    def test_init_bkrepo_missing_password_raises(self, write_kms_files):
        from django.core.management import call_command

        credentials = copy.deepcopy(CREDENTIALS)
        credentials["bkrepo"] = {
            "admin": {"username": "admin", "password": "kms-super-pwd"},
            "default": {"username": "bkpaas3", "password": "kms-bkpaas3-pwd"},
            "addons": {"username": "addons", "password": ""},
        }
        write_kms_files(credentials)

        with pytest.raises(ImproperlyConfigured, match=r"bkrepo\.addons\.password is required"):
            call_command(
                "init_bkrepo",
                "--dry-run=true",
                "--init-enabled=true",
                "--super-username=admin",
                "--bkpaas3-username=bkpaas3",
                "--addons-username=addons",
                "--lesscode-username=lesscode",
            )
