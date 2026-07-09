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
"""运行环境敏感变量加密：开关判定、敏感变量识别、密钥注入

部署时在 BkApp manifest 成型后、下发前做一次统一后处理: 识别敏感变量 → 获取该应用该环境
的 runtime key(从表 AppRuntimeEncryptionKey) → 用 blue-krill cipher 加密并覆盖写入 →
追加统一密钥变量 `BKPAAS_ENCRYPT_SECRET_KEY`,`BKPAAS_ENCRYPTED_ENV_KEYS` 供下游 SDK 解密

加密是增强项：任何环节故障都不得阻断部署,一律降级明文 + warning 日志，密文带自有前缀 `bkpaas_enc$`
"""

import logging
import secrets
from typing import Tuple

from blue_krill.encrypt.handler import EncryptHandler
from cryptography.fernet import Fernet
from django.conf import settings

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import AppRuntimeEncryptionKey, ModuleEnvironment
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar

logger = logging.getLogger(__name__)

# 随容器下发的统一密钥变量名
SECRET_KEY_ENV_NAME = "BKPAAS_ENCRYPT_SECRET_KEY"

# 记录本环境实际被加密的变量 key 清单(逗号分隔,已排序),供下游 SDK 精确定位需解密的变量,
# 加密失败的变量不计入
ENCRYPTED_KEYS_ENV_NAME = "BKPAAS_ENCRYPTED_ENV_KEYS"

# 密文前缀，用于区分这是平台注入的密文
CIPHER_PREFIX = "bkpaas_enc$"


def is_encrypt_enabled(env: ModuleEnvironment) -> bool:
    """
    判定某环境是否启用运行环境敏感变量加密：全局开关与应用级 feature flag 需同时开启。
    """
    if not settings.ENABLE_ENCRYPT_SENSITIVE_ENV_VARS:
        return False
    try:
        return env.application.feature_flag.has_feature(AppFeatureFlag.ENCRYPT_SENSITIVE_ENV_VARS)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to read app-level encrypt feature flag for env %s, treat as disabled", env)
        return False


def collect_sensitive_keys(env: ModuleEnvironment) -> set[str]:
    """汇总敏感环境变量

    两个来源:
    - 增强服务:各 group 的 `should_hidden_fields` ∪ `should_remove_fields`(均为已加前缀大写的 env key),
    - 用户变量:`ConfigVar.is_sensitive == True` 的变量 key。
    """
    keys: set[str] = set()

    # 增强服务(含绑定与共享)声明的敏感字段
    try:
        var_groups = ServiceSharingManager(env.module).get_env_variable_groups(
            env, filter_enabled=True
        ) + mixed_service_mgr.get_env_var_groups(env.get_engine_app(), filter_enabled=True)
        for group in var_groups:
            keys.update(group.should_hidden_fields or [])
            keys.update(group.should_remove_fields or [])
    except Exception:  # noqa: BLE001
        logger.warning("Failed to collect sensitive addon fields for env %s, skip addon keys", env, exc_info=True)

    # 用户标记为敏感的环境变量(global + 当前环境)
    try:
        sensitive_config_vars = ConfigVar.objects.filter(
            module=env.module, environment_id__in=(ENVIRONMENT_ID_FOR_GLOBAL, env.id), is_sensitive=True
        )
        keys.update(var.key for var in sensitive_config_vars)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to collect sensitive config vars for env %s, skip user keys", env, exc_info=True)

    return keys


def _generate_runtime_key() -> str:
    """按当前平台加密算法生成一把 runtime 密钥

    - CLASSIC(Fernet):`Fernet.generate_key()` 生成的 base64 串
    - SHANGMI(SM4CTR):随机 32 位十六进制串(SM4 取前 16 字节为密钥)
    """
    if settings.ENCRYPT_CIPHER_TYPE == "SM4CTR":
        return secrets.token_hex(16)
    return Fernet.generate_key().decode()


def get_or_create_runtime_key(env: ModuleEnvironment) -> str:
    """
    获取该应用该环境的 runtime 密钥,不存在则生成并持久化
    """
    application = env.application
    obj, _ = AppRuntimeEncryptionKey.objects.get_or_create(
        application=application,
        environment=env.environment,
        defaults={
            "key": _generate_runtime_key(),
            "cipher_type": settings.ENCRYPT_CIPHER_TYPE,
            "tenant_id": application.tenant_id,
        },
    )
    return obj.key


def _try_encrypt(handler: EncryptHandler, value: str) -> Tuple[str, bool]:
    """加密单个变量值,返回 (值, 是否成功)

    成功时值 = 外层前缀 `bkpaas_enc$` + blue-krill 原生密文;失败则降级返回明文 + warning
    (不影响其余变量与部署流程),此时第二个返回值为 False
    """
    try:
        return CIPHER_PREFIX + handler.encrypt(value), True
    except Exception:  # noqa: BLE001
        logger.warning("Failed to encrypt a sensitive env var, degrade to plaintext", exc_info=True)
        return value, False


def apply_runtime_encryption(model_res: crd.BkAppResource, env: ModuleEnvironment):
    """统一后处理：对成型 BkApp manifest 中的敏感变量做密文替换,并注入统一密钥变量

    仅处理 global configuration.env 与目标 env 的 overlay 条目(其它环境 overlay 会在部署那个
    环境时用对应 key 处理)。置于 `get_bkapp_resource_for_deploy` 出口,不侵入各 constructor

    :param model_res: 成型的 BkApp 资源对象,将被原地修改
    :param env: 目标部署环境
    """
    # D5:双开关未同时开启 → 直接返回,走原明文注入逻辑
    if not is_encrypt_enabled(env):
        return

    # runtime key 生成/读取失败 → 该应用加密不可用,降级明文 + warning,部署继续
    try:
        key = get_or_create_runtime_key(env)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to get or create runtime key for env %s, degrade to plaintext", env, exc_info=True)
        return

    sensitive_keys = collect_sensitive_keys(env)
    handler = EncryptHandler(secret_key=key)  # type: ignore[arg-type]  # blue-krill 支持 str 密钥

    # 记录实际被加密(未降级明文)的变量 key,注入清单变量供 SDK 精确解密
    encrypted_keys: set[str] = set()

    # 加密 global configuration.env 中的敏感条目
    for var in model_res.spec.configuration.env:
        if var.name in sensitive_keys:
            var.value, ok = _try_encrypt(handler, var.value)
            if ok:
                encrypted_keys.add(var.name)

    # 加密目标 env 的 overlay 敏感条目
    overlay = model_res.spec.envOverlay
    if overlay and overlay.envVariables:
        for ov in overlay.envVariables:
            if ov.envName == env.environment and ov.name in sensitive_keys:
                ov.value, ok = _try_encrypt(handler, ov.value)
                if ok:
                    encrypted_keys.add(ov.name)

    # 注入统一密钥变量(global + 目标 env overlay 各一),确保运行时可见
    _inject_secret_key_var(model_res, env, key)
    # 注入被加密变量清单(供 SDK 精确定位需解密的变量)
    _inject_encrypted_keys_var(model_res, env, sorted(encrypted_keys))


def _inject_secret_key_var(model_res: crd.BkAppResource, env: ModuleEnvironment, key: str):
    """将统一密钥变量 `BKPAAS_ENCRYPT_SECRET_KEY` 注入到 global env 与目标 env overlay。"""
    _inject_env_var(model_res, env, SECRET_KEY_ENV_NAME, key)


def _inject_encrypted_keys_var(model_res: crd.BkAppResource, env: ModuleEnvironment, keys: list[str]):
    """将被加密变量清单 `BKPAAS_ENCRYPTED_ENV_KEYS`(逗号分隔) 注入到 global env 与目标 env overlay。"""
    _inject_env_var(model_res, env, ENCRYPTED_KEYS_ENV_NAME, ",".join(keys))


def _inject_env_var(model_res: crd.BkAppResource, env: ModuleEnvironment, name: str, value: str):
    """覆盖式将单个环境变量注入到 global configuration.env 与目标 env overlay,确保运行时可见。"""
    # 覆盖式写入 global configuration.env
    model_res.spec.configuration.env = [var for var in model_res.spec.configuration.env if var.name != name]
    model_res.spec.configuration.env.append(crd.EnvVar(name=name, value=value))

    # 覆盖式写入目标 env overlay
    overlay = model_res.spec.envOverlay
    if not overlay:
        overlay = model_res.spec.envOverlay = crd.EnvOverlay(envVariables=[])
    env_variables = overlay.envVariables or []
    env_variables = [ov for ov in env_variables if not (ov.envName == env.environment and ov.name == name)]
    env_variables.append(crd.EnvVarOverlay(envName=env.environment, name=name, value=value))
    overlay.envVariables = env_variables
