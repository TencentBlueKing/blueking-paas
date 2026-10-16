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

部署方式沿用 helm-charts 大仓的 KMS 规范：平台组件开关 `PAAS_PLATFORM_KMS_ENABLED` 只读取环境变量，仅接受 "true" 或 "True"；
私钥从环境变量 `BK_PAAS_KMS_PRIVATE_KEY` 读取，信封从文件 `/etc/secrets/bk-paas-kms` 读取。
私钥或信封不可用、解密失败时阻止启动。

信封字段与 settings 的映射见下方绑定及 apiserver/design_notes/platform-kms.md。
字段缺失或为空字符串时沿用原配置；必填项仍为空时阻止启动。未迁移的明文只记录配置项名告警。
"""

import functools
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Tuple
from urllib.parse import unquote, urlsplit, urlunsplit

from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
from django.core.exceptions import ImproperlyConfigured
from dynaconf import LazySettings
from dynaconf.utils.parse_conf import boolean_fix, parse_conf_data

logger = logging.getLogger(__name__)

ENABLED_ENV_VAR = "PAAS_PLATFORM_KMS_ENABLED"
PRIVATE_KEY_ENV_VAR = "BK_PAAS_KMS_PRIVATE_KEY"
# 仅供本地开发覆盖信封路径，chart 不设置
ENVELOPE_PATH_ENV_VAR = "BK_PAAS_KMS_ENVELOPE_PATH"
DEFAULT_ENVELOPE_PATH = "/etc/secrets/bk-paas-kms"

# 敏感配置项，未由信封提供而原配置中仍有值时告警
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
# 开启 KMS 后 chart 不再渲染这些明文，缺失时阻止启动，而不是等到运行时才连接失败或用错密钥：
# SLUG_ENCRYPT_SECRET_KEY 未配置时会退回 BKKRILL_ENCRYPT_SECRET_KEY，用错密钥将无法解密已有数据
REQUIRED_KEYS: Dict[str, str] = {
    "BK_APP_SECRET": "bkapp_id_secret.default.app_secret",
    "BKKRILL_ENCRYPT_SECRET_KEY": "encryption.bk_krill.secret_key",
    "SLUG_ENCRYPT_SECRET_KEY": "encryption.slug.secret_key",
    "ONE_SIMPLE_JWT_AUTH_KEY": "jwt.services.client_key",
}


def _has_url_password(value: Any) -> bool:
    return isinstance(value, str) and bool(urlsplit(value).password)


def _has_es_http_auth(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(host, Mapping) and host.get("http_auth") for host in value)


def _has_mapping_field(field: str) -> Callable[[Any], bool]:
    return lambda value: isinstance(value, Mapping) and bool(value.get(field))


# 只在值中确实带有凭证时才告警的配置项，其余敏感配置项有值即告警
_CREDENTIAL_DETECTORS: Dict[str, Callable[[Any], bool]] = {
    "SENTRY_CONFIG": _has_mapping_field("dsn"),
    "PAAS_ANALYSIS_JWT_CONF": _has_mapping_field("key"),
    "METRIC_CLIENT_TOKEN_DICT": _has_mapping_field("bkmonitor"),
    "ELASTICSEARCH_HOSTS": _has_es_http_auth,
    "PYTHON_BUILDPACK_PIP_INDEX_URL": _has_url_password,
}


def _merge_field(field: str) -> Callable[[LazySettings, str, str], Any]:
    """生成更新字典类配置中单个字段的转换函数，其余字段保持原配置"""

    def merge(settings: LazySettings, key: str, value: str) -> Any:
        original = settings.get(key)
        if original is None:
            original = {}
        if not isinstance(original, Mapping):
            raise ImproperlyConfigured(f"KMS requires {key} to be a mapping")
        if key == "PAAS_ANALYSIS_JWT_CONF" and not original:
            # JWT 还需要 algorithm/iss 等非敏感配置，仅有 key 不能启用客户端。
            logger.warning("PAAS_ANALYSIS_JWT_CONF is disabled, ignoring its KMS key")
            return original
        return {**original, field: value}

    return merge


def _as_is(settings: LazySettings, key: str, value: str) -> Any:
    return value


def _parse_like_env_var(settings: LazySettings, key: str, value: str) -> Any:
    """结构化配置保留原环境变量的 @json/TOML 解析，密码和 Token 则通过 _as_is 按原文返回。"""
    return parse_conf_data(boolean_fix(value), tomlfy=True, box_settings=settings)


_Bindings = Dict[str, Tuple[str, Callable[[LazySettings, str, str], Any]]]

# 配置项: (信封字段路径, 由信封中的值生成配置值的函数)
_APISERVER_BINDINGS: _Bindings = {
    "BK_APP_CODE": ("bkapp_id_secret.default.app_code", _as_is),
    "BK_APP_SECRET": ("bkapp_id_secret.default.app_secret", _as_is),
    "BKKRILL_ENCRYPT_SECRET_KEY": ("encryption.bk_krill.secret_key", _as_is),
    "SLUG_ENCRYPT_SECRET_KEY": ("encryption.slug.secret_key", _as_is),
    "ONE_SIMPLE_JWT_AUTH_KEY": ("jwt.services.client_key", _as_is),
    "PAAS_ANALYSIS_JWT_CONF": ("jwt.paas_analysis.key", _merge_field("key")),
    "HEALTHZ_TOKEN": ("tokens.healthz.token", _as_is),
    "METRIC_CLIENT_TOKEN_DICT": ("tokens.metrics.token", _merge_field("bkmonitor")),
    "AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN": ("tokens.agent_sandbox_daemon.token", _as_is),
    "OTEL_BK_DATA_TOKEN": ("telemetry.default.token", _as_is),
    "SENTRY_CONFIG": ("sentry.default.dsn", _merge_field("dsn")),
    "ELASTICSEARCH_HOSTS": ("elasticsearch.default.hosts", _parse_like_env_var),
    "CELERY_BROKER_URL": ("celery.default.uri", _as_is),
}
_WORKLOADS_BINDINGS: _Bindings = {
    "AGENT_SANDBOX_ROUTER_AUTH_TOKEN": ("tokens.agent_sandbox_router.token", _as_is),
}

# (配置项前缀, mysql 实例名, 加密连接串的环境变量名)，与 get_database_conf 的调用保持一致
_DATABASES: List[Tuple[str, str, str]] = [
    ("", "apiserver", "DATABASE_URL"),
    ("WL_", "workloads", "WL_DATABASE_URL"),
    ("PAAS_LEGACY_", "open_paas", "PAAS_LEGACY_DATABASE_URL"),
    ("BK_CONSOLE_", "open_paas", "PAAS_LEGACY_DATABASE_URL"),
]
_SENTINEL_PASSWORD_KEYS = [
    "SENTINEL_PASSWORD",
    "CELERY_BROKER_SENTINEL_PASSWORD",
    "CELERY_RESULT_BACKEND_SENTINEL_PASSWORD",
]
_REDIS_SCHEMES = ("redis", "rediss", "sentinel")


class KMSSettings:
    """优先返回由信封生成的配置项，其余配置项交给原 dynaconf settings

    只提供 get 接口；这些值按原文返回，不经过 dynaconf 对 "@int"、"@format" 等前缀的解析。
    原 dynaconf 配置内的模板引用仍按原配置解析，不能引用信封覆盖值。
    """

    def __init__(self, base: LazySettings, overrides: Dict[str, Any]):
        self._base = base
        self._overrides = overrides

    def get(self, key: str, default: Any = None, *args, **kwargs) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        return self._base.get(key, default, *args, **kwargs)


def is_platform_kms_enabled() -> bool:
    # 此开关在 Dynaconf 初始化前使用；不能直接 bool()，否则字符串 "false" 也会开启 KMS。
    return os.environ.get(ENABLED_ENV_VAR) in ("true", "True")


def get_kms_credential(path: str) -> Optional[str]:
    """读取信封中不属于 settings 的凭证（如管理命令使用的集群证书、bkrepo 初始化账号）

    未开启 KMS、字段缺失或为空字符串时返回 None。
    """
    if not is_platform_kms_enabled():
        return None
    return _lookup(_decrypt_credentials(), path)


def load_kms_settings(settings: LazySettings) -> LazySettings | KMSSettings:
    """apiserver 配置：未开启 KMS 时原样返回，开启时写入信封中的配置"""
    if not is_platform_kms_enabled():
        return settings

    overrides = build_overrides(settings, _decrypt_credentials())
    kms_settings = KMSSettings(settings, overrides)
    _check_required(kms_settings)
    _warn_plaintext(settings, APISERVER_SENSITIVE_KEYS, overrides.keys())
    return kms_settings


def load_kms_workloads_settings(settings: LazySettings) -> LazySettings | KMSSettings:
    """workloads 配置：未开启 KMS 时原样返回，开启时写入信封中的配置"""
    if not is_platform_kms_enabled():
        return settings

    overrides = _binding_overrides(settings, _decrypt_credentials(), _WORKLOADS_BINDINGS)
    _warn_plaintext(settings, WORKLOADS_SENSITIVE_KEYS, overrides.keys())
    return KMSSettings(settings, overrides)


def build_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    """根据信封生成 apiserver 要覆盖的配置项"""
    overrides = _binding_overrides(settings, credentials, _APISERVER_BINDINGS)
    overrides.update(_database_overrides(settings, credentials))
    overrides.update(_bkrepo_overrides(settings, credentials))
    overrides.update(_docker_registry_overrides(settings, credentials))
    # celery.default.uri 已提供完整的 CELERY_BROKER_URL，不再向其中填入 Redis 密码
    overrides.update(_redis_overrides(settings, credentials, skip=overrides.keys()))
    return overrides


@functools.cache
def _decrypt_credentials() -> Mapping[str, Any]:
    """缓存进程内的信封快照，供 settings 和管理命令共享；信封更新后需重启进程。"""
    private_key = os.environ.get(PRIVATE_KEY_ENV_VAR, "").strip()
    if not private_key:
        raise ImproperlyConfigured(f"KMS requires {PRIVATE_KEY_ENV_VAR}")

    envelope_path = Path(os.environ.get(ENVELOPE_PATH_ENV_VAR) or DEFAULT_ENVELOPE_PATH)
    try:
        envelope = envelope_path.read_text(encoding="utf-8").strip()
        credentials = json.loads(decrypt(envelope=envelope, private_key=private_key))
    except CryptoBackendUnavailableError:
        raise ImproperlyConfigured("KMS SM2/SM4 crypto backend is unavailable") from None
    except (OSError, UnicodeError, ValueError, CryptoError):
        # 不携带原始异常，避免信封或明文内容出现在启动日志中
        raise ImproperlyConfigured("Unable to read or decrypt the KMS credential envelope") from None

    if not isinstance(credentials, dict):
        raise ImproperlyConfigured("The KMS credential envelope must contain a JSON object")
    return credentials


def _check_required(settings: KMSSettings):
    """必需的凭证在信封与原配置中都没有时阻止启动。数据库与 bkrepo 只在配置了对应实例时才要求"""
    required = dict(REQUIRED_KEYS)
    for prefix, instance, _ in _DATABASES:
        if settings.get(f"{prefix}DATABASE_NAME"):
            required[f"{prefix}DATABASE_PASSWORD"] = f"mysql.{instance}.password"
    for key, path in required.items():
        if not settings.get(key):
            raise ImproperlyConfigured(f"{key} is required, provide it by KMS credential {path}")

    if (bkrepo_config := settings.get("BLOBSTORE_BKREPO_CONFIG")) and not bkrepo_config.get("PASSWORD"):
        raise ImproperlyConfigured(
            "BLOBSTORE_BKREPO_CONFIG.PASSWORD is required, provide it by KMS credential bkrepo.default.password"
        )


def _lookup(credentials: Mapping[str, Any], path: str) -> Optional[str]:
    """取出信封中的字符串，字段不存在或为空字符串时返回 None"""
    value: Any = credentials
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    if not isinstance(value, str):
        raise ImproperlyConfigured(f"KMS requires a string at {path}")
    return value if value.strip() else None


def _binding_overrides(settings: LazySettings, credentials: Mapping[str, Any], bindings: _Bindings) -> Dict[str, Any]:
    overrides = {}
    for key, (path, convert) in bindings.items():
        if (value := _lookup(credentials, path)) is not None:
            overrides[key] = convert(settings, key, value)
    return overrides


def _warn_plaintext(settings: LazySettings, sensitive_keys: List[str], provided: Collection[str]):
    for key in sensitive_keys:
        if key in provided or not (value := settings.get(key)):
            continue
        if _CREDENTIAL_DETECTORS.get(key, bool)(value):
            logger.warning("Sensitive setting %s still uses its plaintext config", key)


def _warn_account(key: str, path: Optional[str]):
    if path is None:
        logger.warning("Sensitive setting %s is not provided by KMS, using its plaintext config", key)
    else:
        logger.warning("Sensitive setting %s is not provided by KMS (%s), using its plaintext config", key, path)


def _database_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    overrides = {}
    for prefix, instance, encrypted_url_var in _DATABASES:
        if encrypted_url_var in os.environ:
            raise ImproperlyConfigured(f"KMS does not support the encrypted database url {encrypted_url_var}")
        if not settings.get(f"{prefix}DATABASE_NAME"):
            continue
        if (password := _lookup(credentials, f"mysql.{instance}.password")) is None:
            if settings.get(f"{prefix}DATABASE_PASSWORD"):
                _warn_account(f"{prefix}DATABASE_PASSWORD", f"mysql.{instance}")
            continue
        overrides[f"{prefix}DATABASE_PASSWORD"] = password
        if (username := _lookup(credentials, f"mysql.{instance}.username")) is not None:
            overrides[f"{prefix}DATABASE_USER"] = username
    return overrides


def _redis_overrides(settings: LazySettings, credentials: Mapping[str, Any], skip: Collection[str]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if (sentinel_password := _lookup(credentials, "redis.sentinel.password")) is not None:
        overrides.update(dict.fromkeys(_SENTINEL_PASSWORD_KEYS, sentinel_password))

    password = _lookup(credentials, "redis.default.password")
    # 未配置时，Celery 默认使用 REDIS_URL，随之生效
    for key in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
        if key in skip or not (original := settings.get(key)):
            continue
        urls = original if isinstance(original, (list, tuple)) else [original]
        updated = []
        for url in urls:
            updated_url = url
            has_password = any(urlsplit(single_url).password for single_url in url.split(";"))
            if url.partition("://")[0] not in _REDIS_SCHEMES:
                if has_password:
                    _warn_account(key, "celery.default.uri" if key == "CELERY_BROKER_URL" else None)
            elif password is None:
                if has_password:
                    _warn_account(key, "redis.default")
            else:
                _check_url_safe(password, "redis.default.password")
                updated_url = _with_password(url, password, key)
            updated.append(updated_url)
        if isinstance(original, (list, tuple)):
            overrides[key] = type(original)(updated)
        else:
            overrides[key] = updated[0]
    return overrides


def _bkrepo_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    if not (bkrepo_config := settings.get("BLOBSTORE_BKREPO_CONFIG")):
        return {}
    if (password := _lookup(credentials, "bkrepo.default.password")) is None:
        if bkrepo_config.get("PASSWORD"):
            _warn_account("BLOBSTORE_BKREPO_CONFIG", "bkrepo.default")
        return {}
    username = _lookup(credentials, "bkrepo.default.username")
    return {
        "BLOBSTORE_BKREPO_CONFIG": {
            **bkrepo_config,
            "USERNAME": bkrepo_config.get("USERNAME") if username is None else username,
            "PASSWORD": password,
        }
    }


def _docker_registry_overrides(settings: LazySettings, credentials: Mapping[str, Any]) -> Dict[str, Any]:
    """chart 在启用外部镜像仓库时使用 registry.external 的账号，否则使用 bkrepo.default 的账号，
    此处按原配置中的用户名选出对应的一组"""
    accounts = []
    for instance in ("registry.external", "bkrepo.default"):
        username, password = _lookup(credentials, f"{instance}.username"), _lookup(credentials, f"{instance}.password")
        if username is not None and password is not None:
            accounts.append((username, password))

    overrides = {}
    for prefix in ("SMART_DOCKER", "APP_DOCKER"):
        username = settings.get(f"{prefix}_USERNAME")
        for account_username, account_password in accounts:
            if account_username == username:
                overrides[f"{prefix}_PASSWORD"] = account_password
                break
    return overrides


def _check_url_safe(value: str, path: str):
    """要原样填入连接串的凭证

    redis-py 与 blue_krill 不对连接串中的密码做 URL 解码，而 kombu 会，因此凭证只能原样填入，
    不能包含截断连接串的字符，也不能包含会被 URL 解码改变的内容，否则各组件解析出的密码不一致。
    """
    if any(c in value for c in "/?#;") or any(ord(c) < 32 or ord(c) == 127 for c in value) or unquote(value) != value:
        raise ImproperlyConfigured(f"KMS credential at {path} contains characters unsupported in urls")


def _with_password(url: str, password: str, key: str) -> str:
    """将密码填入连接串，保留原有的用户名，支持以 ";" 分隔的多个 sentinel 地址"""
    results = []
    for single_url in url.split(";"):
        parts = urlsplit(single_url)
        if not parts.scheme or not parts.hostname:
            raise ImproperlyConfigured(f"Invalid connection url in {key}")
        host = parts.netloc.rpartition("@")[2]
        results.append(urlunsplit(parts._replace(netloc=f"{parts.username or ''}:{password}@{host}")))
    return ";".join(results)
