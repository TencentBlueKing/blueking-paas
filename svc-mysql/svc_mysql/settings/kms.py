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

"""从 KMS 信封加载敏感配置；四个独立构建的增强服务保留相同实现。

私钥由 BK_PAAS_KMS_PRIVATE_KEY 注入，信封默认挂载到 /etc/secrets/bk-paas-kms。
开启 PAAS_PLATFORM_KMS_ENABLED 后解密失败会阻止启动；未提供的字段沿用环境变量。
信封值按原文使用，不解析 $VAR；明文回退告警仅记录变量名。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Collection, Dict, Mapping, Optional

import environ
from bk_kms import CryptoBackendUnavailableError, CryptoError, decrypt
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

ENABLED_ENV_VAR = "PAAS_PLATFORM_KMS_ENABLED"
PRIVATE_KEY_ENV_VAR = "BK_PAAS_KMS_PRIVATE_KEY"
# 仅供本地开发覆盖信封路径，chart 不设置
ENVELOPE_PATH_ENV_VAR = "BK_PAAS_KMS_ENVELOPE_PATH"
DEFAULT_ENVELOPE_PATH = "/etc/secrets/bk-paas-kms"


class KMSEnv(environ.Env):
    """优先返回信封提供的值，其余环境变量照常读取"""

    def __init__(self, credentials: Mapping[str, str], **scheme):
        super().__init__(**scheme)
        self._credentials = credentials

    def get_value(self, var, cast=None, default=environ.Env.NOTSET, parse_default=False):
        if var in self._credentials:
            # 不调用父类，避免 django-environ 将以 "$" 开头的信封值当作环境变量引用。
            return self.parse_value(self._credentials[var], cast)
        return super().get_value(var, cast=cast, default=default, parse_default=parse_default)


def is_kms_enabled() -> bool:
    # 此开关在 django-environ 初始化前读取；不能直接 bool()，否则字符串 "false" 也会开启 KMS。
    return os.environ.get(ENABLED_ENV_VAR) in ("true", "True")


def get_env(
    bindings: Mapping[str, str],
    sensitive_vars: Collection[str] = (),
    required_vars: Collection[str] = (),
    reject_database_url: bool = False,
    **scheme,
) -> environ.Env:
    """未开启 KMS 时返回普通的 environ.Env，开启时返回优先读取信封的 KMSEnv

    :param bindings: 环境变量名到信封字段路径的映射
    :param sensitive_vars: 未由信封提供而环境变量中仍有值时告警的环境变量
    :param required_vars: 信封与环境变量都未提供时阻止启动的环境变量。开启 KMS 后 chart 会清空这些明文，
        缺失时应在启动时报错，而不是等到运行时连接失败或使用代码中公开的默认密钥
    :param reject_database_url: DATABASE_URL 会绕过逐字段的 KMS 凭证时，拒绝该连接串配置
    """
    if not is_kms_enabled():
        return environ.Env(**scheme)

    # 完整连接串会绕过逐字段的 KMS 凭证，开启 KMS 后应改用独立的 MYSQL_* 配置。
    if reject_database_url and os.environ.get("DATABASE_URL"):
        raise ImproperlyConfigured(
            "KMS does not support DATABASE_URL; configure the database with MYSQL_HOST, MYSQL_PORT, "
            "MYSQL_NAME, MYSQL_USER, and MYSQL_PASSWORD"
        )

    credentials = build_credentials(_decrypt_envelope(), bindings)
    for var in required_vars:
        if var not in credentials and not os.environ.get(var):
            hint = f", provide it by KMS credential {bindings[var]}" if var in bindings else ""
            raise ImproperlyConfigured(f"{var} is required{hint}")
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
    """取出信封中的字符串；缺失或空字符串可回退，已存在的错误节点类型必须报错。"""
    value: Any = envelope
    parts = path.split(".")
    for index, part in enumerate(parts):
        if not isinstance(value, Mapping):
            raise ImproperlyConfigured(f"KMS requires an object at {'.'.join(parts[:index])}")
        if part not in value:
            return None
        value = value[part]
    if not isinstance(value, str):
        raise ImproperlyConfigured(f"KMS requires a string at {path}")
    return value if value.strip() else None
