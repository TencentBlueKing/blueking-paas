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

from collections.abc import Mapping

from blue_krill.encrypt.handler import EncryptHandler
from django.conf import settings

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import AppEnvEncryptionKey, ModuleEnvironment
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar

# 密钥的环境变量名
SECRET_KEY_ENV_VAR_NAME = "BKPAAS_ENCRYPT_SECRET_KEY"

# 加密了的环境变量KEYS，逗号分割，字典序
ENCRYPTED_KEYS_ENV_NAME = "BKPAAS_ENCRYPTED_ENV_KEYS"

# 密文前缀，用于区分这是平台注入的密文
CIPHER_PREFIX = "bkpaas_enc$"


def is_encrypted_secret_env_injection_enabled(env: ModuleEnvironment) -> bool:
    """判断该 env 是否启用敏感环境变量密文注入功能"""
    return env.application.feature_flag.has_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION)


def collect_sensitive_keys(env: ModuleEnvironment) -> set[str]:
    """汇总敏感环境变量

    两个来源:
    - 增强服务:各 group 的 `should_hidden_fields` ∪ `should_remove_fields`(均为已加前缀大写的 env key),
    - 用户变量:`ConfigVar.is_sensitive == True` 的变量 key。
    """
    keys: set[str] = set()

    # 增强服务(含绑定与共享)声明的敏感字段
    var_groups = ServiceSharingManager(env.module).get_env_variable_groups(
        env, filter_enabled=True
    ) + mixed_service_mgr.get_env_var_groups(env.get_engine_app(), filter_enabled=True)
    for group in var_groups:
        keys.update(group.should_hidden_fields or [])
        keys.update(group.should_remove_fields or [])

    # 用户标记为敏感的环境变量(global + 当前环境)
    sensitive_config_vars = ConfigVar.objects.filter(
        module=env.module, environment_id__in=(ENVIRONMENT_ID_FOR_GLOBAL, env.id), is_sensitive=True
    )
    keys.update(var.key for var in sensitive_config_vars)

    return keys


def get_or_create_env_encryption_key(env: ModuleEnvironment, cipher_type: str) -> tuple[AppEnvEncryptionKey, bool]:
    """
    获取该应用该环境的加密密钥, 不存在则生成并持久化
    """
    application = env.application
    return AppEnvEncryptionKey.objects.get_or_create(
        application=application,
        environment=env.environment,
        defaults={
            "key": AppEnvEncryptionKey.generate_key(cipher_type),
            "cipher_type": cipher_type,
            "tenant_id": application.tenant_id,
        },
    )


def rotate_env_encryption_key(env: ModuleEnvironment, cipher_type: str) -> tuple[AppEnvEncryptionKey, bool]:
    """Rotate the encryption key for an application environment.

    Existing workloads retain the old key from their environment until they are
    redeployed. The next deployment injects this replacement key and encrypts
    sensitive values with it.
    """
    application = env.application
    return AppEnvEncryptionKey.objects.update_or_create(
        application=application,
        environment=env.environment,
        defaults={
            "key": AppEnvEncryptionKey.generate_key(cipher_type),
            "cipher_type": cipher_type,
            "tenant_id": application.tenant_id,
        },
    )


def _encrypt_value(handler: EncryptHandler, value: str) -> str:
    """加密单个变量值,返回带外层前缀 `bkpaas_enc$` 的密文。"""
    return CIPHER_PREFIX + handler.encrypt(value)


def is_encrypted_value(value: str) -> bool:
    """Return whether a value was encrypted by the PaaS environment injector."""
    return value.startswith(CIPHER_PREFIX)


def encrypt_sensitive_values(
    env: ModuleEnvironment, values: Mapping[str, str], sensitive_keys: set[str]
) -> tuple[dict[str, str], set[str]]:
    """Encrypt sensitive entries for one environment with a single environment key.

    Returns the transformed values and the keys that were actually encrypted.
    """
    encrypted_keys = set(values).intersection(sensitive_keys)
    if not encrypted_keys or not is_encrypted_secret_env_injection_enabled(env):
        return dict(values), set()

    encryption_key, _ = get_or_create_env_encryption_key(env, settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE)
    handler = EncryptHandler(encrypt_cipher_type=encryption_key.cipher_type, secret_key=encryption_key.key)
    encrypted_values = dict(values)
    for key in encrypted_keys:
        encrypted_values[key] = _encrypt_value(handler, encrypted_values[key])
    return encrypted_values, encrypted_keys


def get_runtime_encryption_env_vars(env: ModuleEnvironment, encrypted_keys: set[str]) -> dict[str, str]:
    """Build the runtime metadata needed to decrypt the supplied encrypted keys."""
    if not encrypted_keys or not is_encrypted_secret_env_injection_enabled(env):
        return {}

    encryption_key, _ = get_or_create_env_encryption_key(env, settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE)
    return {
        SECRET_KEY_ENV_VAR_NAME: encryption_key.key,
        ENCRYPTED_KEYS_ENV_NAME: ",".join(sorted(encrypted_keys)),
    }
