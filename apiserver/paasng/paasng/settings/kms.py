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

"""从 KMS 信封加载平台自身的敏感配置，须在读取任何配置项之前调用

开关 `PAAS_PLATFORM_KMS_ENABLED` 只读取环境变量，仅接受 "true" 或 "True"。信封不可读或解密失败时阻止启动。
信封明文结构：

    {
      # 原样搬入原来以明文环境变量提供的配置，键为环境变量名，值的解析规则与环境变量完全一致
      "env": {
        "PAAS_BK_APP_SECRET": "...",
        "PAAS_BKKRILL_ENCRYPT_SECRET_KEY": "...",
        "PAAS_HEALTHZ_TOKEN": "...",
        "PAAS_METRIC_CLIENT_TOKEN_DICT": "{bkmonitor='...'}",
        "PAAS_WL_AGENT_SANDBOX_ROUTER_AUTH_TOKEN": "..."
      },
      # 账号密码按 "类型.实例.字段" 分层，与 env 中的同名配置同时提供时以此处为准
      "mysql": {
        "default": {"username": "...", "password": "..."},    # DATABASE_*
        "workloads": {"username": "...", "password": "..."},  # WL_DATABASE_*
        "legacy": {"username": "...", "password": "..."},     # PAAS_LEGACY_DATABASE_*
        "console": {"username": "...", "password": "..."}     # BK_CONSOLE_DATABASE_*
      },
      "redis": {
        "default": {"password": "..."},  # 填入 REDIS_URL 及 Redis 类型的 CELERY_BROKER_URL/CELERY_RESULT_BACKEND
        "sentinel": {"password": "..."}  # 覆盖各 SENTINEL_PASSWORD
      },
      "rabbitmq": {"default": {"username": "...", "password": "..."}},  # 填入 amqp 类型的 CELERY_BROKER_URL
      "bkrepo": {"default": {"username": "...", "password": "..."}}     # BLOBSTORE_BKREPO_CONFIG
    }

各部分均可省略。信封未提供、但原配置中仍有明文的敏感配置项照常生效，并输出只含配置项名的告警。

Redis、RabbitMQ 连接串仍由原配置提供（可不带密码），凭证原样填入并覆盖连接串中原有的账号密码，
因此这些凭证不能包含 "/"、"?"、"#" 及 "%XX" 形式的内容，RabbitMQ 用户名不能包含 ":"。
"""

import functools
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Set, Tuple
from urllib.parse import unquote, urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured
from dynaconf import LazySettings
from dynaconf.utils.parse_conf import boolean_fix

logger = logging.getLogger(__name__)

ENABLED_ENV_VAR = "PAAS_PLATFORM_KMS_ENABLED"
ENVELOPE_PATH_ENV_VAR = "PAAS_PLATFORM_KMS_ENVELOPE_PATH"
PRIVATE_KEY_PATH_ENV_VAR = "PAAS_PLATFORM_KMS_PRIVATE_KEY_PATH"
DEFAULT_ENVELOPE_PATH = "/etc/kms/envelope"
DEFAULT_PRIVATE_KEY_PATH = "/etc/kms/privateKey"

APISERVER_ENVVAR_PREFIX = "PAAS"
WORKLOADS_ENVVAR_PREFIX = "PAAS_WL"

# 敏感配置项（不含环境变量前缀），未由信封提供而原配置中仍有值时告警
APISERVER_SENSITIVE_KEYS = [
    "BK_APP_SECRET",
    "BKKRILL_ENCRYPT_SECRET_KEY",
    "SECRET_KEY",
    "SLUG_ENCRYPT_SECRET_KEY",
    "PAAS_LEGACY_DB_ENCRYPT_KEY",
    "IAM_APP_SECRET",
    "BKAUTH_TOKEN_SECRET_KEY",
    "ONE_SIMPLE_JWT_AUTH_KEY",
    "PAAS_SERVICE_JWT_CLIENTS",
    "PAAS_ANALYSIS_JWT_CONF",
    "HEALTHZ_TOKEN",
    "METRIC_CLIENT_TOKEN_DICT",
    "OTEL_BK_DATA_TOKEN",
    "BK_AUDIT_DATA_TOKEN",
    "SENTRY_CONFIG",
    "CLI_AUTH_SECRET",
    "BUILD_TOKEN_SIGNING_KEYS",
    "FRONTEND_ENCRYPT_PRIVATE_KEY_BASE64",
    "IWIKI_API_RIO_GW_TOKEN",
    "MK_SEARCH_API_RIO_GW_TOKEN",
    "MK_SEARCH_API_PRIVATE_TOKEN",
    "AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN",
    "SMART_DOCKER_PASSWORD",
    "APP_DOCKER_PASSWORD",
    "BLOBSTORE_S3_SECRET_KEY",
    "RGW_SECRET_ACCESS_KEY",
    "SENTINEL_PASSWORD",
    "CELERY_BROKER_SENTINEL_PASSWORD",
    "CELERY_RESULT_BACKEND_SENTINEL_PASSWORD",
    "DEFAULT_CACHE_CONFIG",
    "PLUGIN_REPO_CONF",
    "SERVICES_VENDOR_CONFIGS",
    "PAAS_X_BK_DATA_DB_CONF",
    "ELASTICSEARCH_HOSTS",
]
WORKLOADS_SENSITIVE_KEYS = ["AGENT_SANDBOX_ROUTER_AUTH_TOKEN", "PYTHON_BUILDPACK_PIP_INDEX_URL"]


def _has_url_password(value: Any) -> bool:
    return isinstance(value, str) and bool(urlsplit(value).password)


def _has_es_http_auth(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(host, Mapping) and host.get("http_auth") for host in value)


# 只在值中确实带有凭证时才告警的配置项，其余敏感配置项有值即告警
_CREDENTIAL_DETECTORS: Dict[str, Callable[[Any], bool]] = {
    "ELASTICSEARCH_HOSTS": _has_es_http_auth,
    "PYTHON_BUILDPACK_PIP_INDEX_URL": _has_url_password,
}

# (配置项前缀, mysql 实例名, 加密连接串的环境变量名)，与 get_database_conf 的调用保持一致
_DATABASES: List[Tuple[str, str, str]] = [
    ("", "default", "DATABASE_URL"),
    ("WL_", "workloads", "WL_DATABASE_URL"),
    ("PAAS_LEGACY_", "legacy", "PAAS_LEGACY_DATABASE_URL"),
    ("BK_CONSOLE_", "console", "PAAS_LEGACY_DATABASE_URL"),
]
_SENTINEL_PASSWORD_KEYS = [
    "SENTINEL_PASSWORD",
    "CELERY_BROKER_SENTINEL_PASSWORD",
    "CELERY_RESULT_BACKEND_SENTINEL_PASSWORD",
]
_REDIS_SCHEMES = ("redis", "rediss", "sentinel")
_AMQP_SCHEMES = ("amqp", "amqps", "pyamqp")


class KMSSettings:
    """优先返回由信封中账号密码生成的配置项，其余配置项交给原 dynaconf settings

    这些值按原文返回，不经过 dynaconf 对 "@int"、"@format" 等前缀的解析。
    """

    def __init__(self, base: LazySettings, overrides: Dict[str, Any]):
        self._base = base
        self._overrides = overrides

    def get(self, key: str, default: Any = None, *args, **kwargs) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        return self._base.get(key, default, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


def is_platform_kms_enabled() -> bool:
    return os.environ.get(ENABLED_ENV_VAR) in ("true", "True")


def load_kms_settings(settings: LazySettings) -> LazySettings | KMSSettings:
    """apiserver 配置：未开启 KMS 时原样返回，开启时写入信封中的配置"""
    if not is_platform_kms_enabled():
        return settings

    credentials = _decrypt_credentials()
    env_vars = _get_section(credentials, "env")
    for name in env_vars:
        if not name.startswith(f"{APISERVER_ENVVAR_PREFIX}_"):
            logger.warning("KMS env %s is ignored: name must start with %s_", name, APISERVER_ENVVAR_PREFIX)
    provided = _apply_env_vars(settings, env_vars, APISERVER_ENVVAR_PREFIX)
    if not settings.get("BKKRILL_ENCRYPT_SECRET_KEY"):
        raise ImproperlyConfigured("BKKRILL_ENCRYPT_SECRET_KEY is required")

    overrides = build_account_overrides(settings, credentials)
    _warn_plaintext(settings, APISERVER_SENSITIVE_KEYS, provided | overrides.keys())
    return KMSSettings(settings, overrides)


def load_kms_workloads_settings(settings: LazySettings) -> LazySettings:
    """workloads 配置：只处理信封 env 中以 PAAS_WL_ 开头的配置"""
    if not is_platform_kms_enabled():
        return settings

    env_vars = _get_section(_decrypt_credentials(), "env")
    provided = _apply_env_vars(settings, env_vars, WORKLOADS_ENVVAR_PREFIX)
    _warn_plaintext(settings, WORKLOADS_SENSITIVE_KEYS, provided)
    return settings


def build_account_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    """根据信封中的账号密码，生成要覆盖的配置项"""
    return {
        **_database_overrides(settings, credentials),
        **_redis_overrides(settings, credentials),
        **_bkrepo_overrides(settings, credentials),
    }


@functools.cache
def _decrypt_credentials() -> Mapping[str, Any]:
    try:
        from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
    except ImportError:
        raise ImproperlyConfigured("KMS requires the bk-kms-sdk package") from None

    envelope_path = Path(os.environ.get(ENVELOPE_PATH_ENV_VAR) or DEFAULT_ENVELOPE_PATH)
    private_key_path = Path(os.environ.get(PRIVATE_KEY_PATH_ENV_VAR) or DEFAULT_PRIVATE_KEY_PATH)
    try:
        envelope = envelope_path.read_text(encoding="utf-8").strip()
        private_key = private_key_path.read_text(encoding="utf-8").strip()
        credentials = json.loads(decrypt(envelope=envelope, private_key=private_key))
    except CryptoBackendUnavailableError:
        raise ImproperlyConfigured("KMS SM2/SM4 crypto backend is unavailable") from None
    except (OSError, UnicodeError, ValueError, CryptoError):
        # 不携带原始异常，避免信封或明文内容出现在启动日志中
        raise ImproperlyConfigured("Unable to read or decrypt the KMS credential envelope") from None

    if not isinstance(credentials, dict):
        raise ImproperlyConfigured("The KMS credential envelope must contain a JSON object")
    return credentials


def _get_section(credentials: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    section = credentials.get(name, {})
    if not isinstance(section, Mapping):
        raise ImproperlyConfigured(f"KMS requires an object at {name}")
    return section


def _apply_env_vars(settings: LazySettings, env_vars: Mapping[str, Any], envvar_prefix: str) -> Set[str]:
    """按 dynaconf 读取环境变量的规则写入配置，返回写入的配置项名"""
    provided = set()
    for name, value in env_vars.items():
        if not name.startswith(f"{envvar_prefix}_"):
            continue
        key = name[len(envvar_prefix) + 1 :]
        if isinstance(value, str):
            settings.set(key, boolean_fix(value), loader_identifier="kms", tomlfy=True)
        else:
            settings.set(key, value, loader_identifier="kms")
        provided.add(key.split("__")[0])
    return provided


def _warn_plaintext(settings: LazySettings, sensitive_keys: List[str], provided: Collection[str]):
    for key in sensitive_keys:
        if key in provided or not (value := settings.get(key)):
            continue
        if _CREDENTIAL_DETECTORS.get(key, bool)(value):
            logger.warning("Sensitive setting %s is not provided by KMS, using its plaintext config", key)


def _database_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    overrides = {}
    for prefix, instance, encrypted_url_var in _DATABASES:
        if encrypted_url_var in os.environ:
            raise ImproperlyConfigured(f"KMS does not support the encrypted database url {encrypted_url_var}")
        if not settings.get(f"{prefix}DATABASE_NAME"):
            continue
        if _lookup(credentials, ("mysql", instance)) is None:
            if settings.get(f"{prefix}DATABASE_PASSWORD"):
                _warn_account(f"{prefix}DATABASE_PASSWORD", f"mysql.{instance}")
            continue
        overrides[f"{prefix}DATABASE_USER"] = _require(credentials, ("mysql", instance, "username"))
        overrides[f"{prefix}DATABASE_PASSWORD"] = _require(credentials, ("mysql", instance, "password"))
    return overrides


def _redis_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if _lookup(credentials, ("redis", "sentinel")) is not None:
        sentinel_password = _require(credentials, ("redis", "sentinel", "password"))
        overrides.update(dict.fromkeys(_SENTINEL_PASSWORD_KEYS, sentinel_password))

    # 未配置时，Celery 默认使用 REDIS_URL，随之生效
    for key in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
        if not (url := settings.get(key)):
            continue
        scheme = url.partition("://")[0]
        if scheme in _REDIS_SCHEMES:
            instance, username_path = ("redis", "default"), None
        elif scheme in _AMQP_SCHEMES:
            instance, username_path = ("rabbitmq", "default"), ("rabbitmq", "default", "username")
        else:
            raise ImproperlyConfigured(f"KMS does not support the scheme of {key}")

        if _lookup(credentials, instance) is None:
            if any(urlsplit(single_url).password for single_url in url.split(";")):
                _warn_account(key, ".".join(instance))
            continue
        password = _require_url_safe(credentials, (*instance, "password"))
        username = _require_url_safe(credentials, username_path, extra_chars=":") if username_path else None
        overrides[key] = _with_credentials(url, password, key, username=username)
    return overrides


def _bkrepo_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    if not (bkrepo_config := settings.get("BLOBSTORE_BKREPO_CONFIG")):
        return {}
    if _lookup(credentials, ("bkrepo", "default")) is None:
        if bkrepo_config.get("PASSWORD"):
            _warn_account("BLOBSTORE_BKREPO_CONFIG", "bkrepo.default")
        return {}
    return {
        "BLOBSTORE_BKREPO_CONFIG": {
            **bkrepo_config,
            "USERNAME": _require(credentials, ("bkrepo", "default", "username")),
            "PASSWORD": _require(credentials, ("bkrepo", "default", "password")),
        }
    }


def _warn_account(key: str, path: str):
    logger.warning("Sensitive setting %s is not provided by KMS (%s), using its plaintext config", key, path)


def _lookup(credentials: Mapping[str, Any], path: Tuple[str, ...]) -> Any:
    """取出信封中的值，路径不存在时返回 None"""
    value: Any = credentials
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _require(credentials: Mapping[str, Any], path: Tuple[str, ...]) -> str:
    value = _lookup(credentials, path)
    if not isinstance(value, str) or not value.strip():
        raise ImproperlyConfigured(f"KMS requires a non-empty string at {'.'.join(path)}")
    return value


def _require_url_safe(credentials: Mapping[str, Any], path: Tuple[str, ...], extra_chars: str = "") -> str:
    """取出要原样填入连接串的凭证

    redis-py 与 blue_krill 不对连接串中的密码做 URL 解码，而 kombu 会，因此凭证只能原样填入，
    不能包含截断连接串的字符，也不能包含会被 URL 解码改变的内容，否则各组件解析出的密码不一致。
    """
    value = _require(credentials, path)
    if any(c in value for c in "/?#" + extra_chars) or unquote(value) != value:
        raise ImproperlyConfigured(f"KMS credential at {'.'.join(path)} contains characters unsupported in urls")
    return value


def _with_credentials(url: str, password: str, key: str, username: Optional[str] = None) -> str:
    """将密码（以及用户名）填入连接串，支持以 ";" 分隔的多个 sentinel 地址

    :param username: 为 None 时保留连接串中原有的用户名
    """
    results = []
    for single_url in url.split(";"):
        parts = urlsplit(single_url)
        if not parts.scheme or not parts.hostname:
            raise ImproperlyConfigured(f"Invalid connection url in {key}")
        user = (parts.username or "") if username is None else username
        host = parts.netloc.rpartition("@")[2]
        results.append(urlunsplit(parts._replace(netloc=f"{user}:{password}@{host}")))
    return ";".join(results)
