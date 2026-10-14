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

"""从 KMS 信封加载增强服务的敏感配置，各增强服务使用内容相同的本文件

部署约定与 helm-charts 大仓的 KMS 规范一致：开关 `ENABLE_KMS` 只读取环境变量，仅接受 "true" 或 "True"；
私钥从环境变量 `BK_PAAS_KMS_PRIVATE_KEY` 读取，信封从文件 `/etc/secrets/bk-paas-kms` 读取。
私钥或信封不可用、解密失败时阻止启动。

信封明文按 "凭证类型.实例.字段" 分层，各增强服务在 settings 中声明环境变量与字段路径的对应关系，
其他字段忽略。字段缺失或为空字符串时视为未提供，环境变量中仍有明文的敏感配置照常生效，
并输出只含环境变量名的告警。信封中的值按原文使用，不做 "$VAR" 形式的代理解析。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Collection, Dict, Mapping, Optional

import environ
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

ENABLED_ENV_VAR = "ENABLE_KMS"
PRIVATE_KEY_ENV_VAR = "BK_PAAS_KMS_PRIVATE_KEY"
# 仅供本地开发覆盖信封路径，chart 不设置
ENVELOPE_PATH_ENV_VAR = "BK_PAAS_KMS_ENVELOPE_PATH"
DEFAULT_ENVELOPE_PATH = "/etc/secrets/bk-paas-kms"

# 带密码的完整连接串，无法只替换其中的密码
_UNSUPPORTED_ENV_VARS = ["DATABASE_URL"]


class KMSEnv(environ.Env):
    """优先返回信封提供的值，其余环境变量照常读取"""

    def __init__(self, credentials: Mapping[str, str], **scheme):
        super().__init__(**scheme)
        self._credentials = credentials

    def get_value(self, var, cast=None, default=environ.Env.NOTSET, parse_default=False):
        if var in self._credentials:
            return self.parse_value(self._credentials[var], cast)
        return super().get_value(var, cast=cast, default=default, parse_default=parse_default)


def is_kms_enabled() -> bool:
    return os.environ.get(ENABLED_ENV_VAR) in ("true", "True")


def get_env(
    bindings: Mapping[str, str],
    sensitive_vars: Collection[str] = (),
    required_vars: Collection[str] = (),
    **scheme,
) -> environ.Env:
    """未开启 KMS 时返回普通的 environ.Env，开启时返回优先读取信封的 KMSEnv

    :param bindings: 环境变量名到信封字段路径的映射
    :param sensitive_vars: 未由信封提供而环境变量中仍有值时告警的环境变量
    :param required_vars: 信封与环境变量都未提供时阻止启动的环境变量
    """
    if not is_kms_enabled():
        return environ.Env(**scheme)

    for var in _UNSUPPORTED_ENV_VARS:
        if os.environ.get(var):
            raise ImproperlyConfigured(f"KMS does not support {var}")

    credentials = build_credentials(_decrypt_envelope(), bindings)
    for var in required_vars:
        if var not in credentials and not os.environ.get(var):
            raise ImproperlyConfigured(f"{var} is required")
    for var in sensitive_vars:
        if var not in credentials and os.environ.get(var):
            logger.warning("Sensitive setting %s is not provided by KMS, using its plaintext config", var)
    return KMSEnv(credentials, **scheme)


def build_credentials(envelope: Mapping[str, Any], bindings: Mapping[str, str]) -> Dict[str, str]:
    """取出信封中已提供的字段，返回环境变量名到值的映射"""
    credentials = {}
    for var, path in bindings.items():
        if (value := _lookup(envelope, path)) is not None:
            credentials[var] = value
    return credentials


def _decrypt_envelope() -> Mapping[str, Any]:
    private_key = os.environ.get(PRIVATE_KEY_ENV_VAR, "").strip()
    if not private_key:
        raise ImproperlyConfigured(f"KMS requires {PRIVATE_KEY_ENV_VAR}")

    try:
        from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
    except ImportError:
        raise ImproperlyConfigured("KMS requires the bk-kms-sdk package") from None

    envelope_path = Path(os.environ.get(ENVELOPE_PATH_ENV_VAR) or DEFAULT_ENVELOPE_PATH)
    try:
        envelope = envelope_path.read_text(encoding="utf-8").strip()
        content = json.loads(decrypt(envelope=envelope, private_key=private_key))
    except CryptoBackendUnavailableError:
        raise ImproperlyConfigured("KMS SM2/SM4 crypto backend is unavailable") from None
    except (OSError, UnicodeError, ValueError, CryptoError):
        # 不携带原始异常，避免信封或明文内容出现在启动日志中
        raise ImproperlyConfigured("Unable to read or decrypt the KMS credential envelope") from None

    if not isinstance(content, dict):
        raise ImproperlyConfigured("The KMS credential envelope must contain a JSON object")
    return content


def _lookup(envelope: Mapping[str, Any], path: str) -> Optional[str]:
    """取出信封中的字符串，字段不存在或为空字符串时返回 None"""
    value: Any = envelope
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    if value is None:
        return None
    if not isinstance(value, str):
        raise ImproperlyConfigured(f"KMS requires a string at {path}")
    return value if value.strip() else None
