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

from blue_krill.encrypt.handler import EncryptHandler
from django.conf import settings

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import AppEnvEncryptionKey, ModuleEnvironment
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar

SECRET_KEY_ENV_NAME = "BKPAAS_ENCRYPT_SECRET_KEY"

# 逗号分割，字典序
ENCRYPTED_KEYS_ENV_NAME = "BKPAAS_ENCRYPTED_ENV_KEYS"

# 密文前缀，用于区分这是平台注入的密文
CIPHER_PREFIX = "bkpaas_enc$"


def is_encrypted_secret_env_injection_enabled(env: ModuleEnvironment) -> bool:
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


def get_or_create_env_encryption_key(env: ModuleEnvironment, cipher_type: str):
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


def _encrypt_value(handler: EncryptHandler, value: str) -> str:
    """加密单个变量值,返回带外层前缀 `bkpaas_enc$` 的密文。"""
    return CIPHER_PREFIX + handler.encrypt(value)


def apply_encrypted_secret_env_injection(model_res: crd.BkAppResource, env: ModuleEnvironment):
    """统一后处理：对成型 BkApp manifest 中的敏感变量做密文替换,并注入统一密钥变量

    仅处理 global configuration.env 与目标 env 的 overlay 条目(其它环境 overlay 会在部署那个
    环境时用对应 key 处理)。置于 `get_bkapp_resource_for_deploy` 出口,不侵入各 constructor

    :param model_res: 成型的 BkApp 资源对象,将被原地修改
    :param env: 目标部署环境
    """
    if not is_encrypted_secret_env_injection_enabled(env):
        return

    env_encryption_obj, _ = get_or_create_env_encryption_key(env, settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE)
    sensitive_keys = collect_sensitive_keys(env)
    handler = EncryptHandler(secret_key=env_encryption_obj.key)  # type: ignore[arg-type]  # blue-krill 支持 str 密钥

    encrypted_keys: set[str] = set()

    # 加密 global configuration.env 中的敏感条目
    for var in model_res.spec.configuration.env:
        if var.name in sensitive_keys:
            var.value = _encrypt_value(handler, var.value)
            encrypted_keys.add(var.name)

    # 加密目标 env 的 overlay 敏感条目
    overlay = model_res.spec.envOverlay
    if overlay and overlay.envVariables:
        for ov in overlay.envVariables:
            if ov.envName == env.environment and ov.name in sensitive_keys:
                ov.value = _encrypt_value(handler, ov.value)
                encrypted_keys.add(ov.name)

    # 注入统一密钥变量与被加密变量清单到目标 env overlay,供运行时 SDK 使用
    _inject_env_overlay_var(model_res, env, SECRET_KEY_ENV_NAME, env_encryption_obj.key)
    _inject_env_overlay_var(model_res, env, ENCRYPTED_KEYS_ENV_NAME, ",".join(sorted(encrypted_keys)))


def _inject_env_overlay_var(model_res: crd.BkAppResource, env: ModuleEnvironment, name: str, value: str):
    """覆盖式将单个环境变量注入到目标 env overlay,供运行时使用。"""
    overlay = model_res.spec.envOverlay
    if not overlay:
        overlay = model_res.spec.envOverlay = crd.EnvOverlay(envVariables=[])
    env_variables = overlay.envVariables or []
    env_variables = [ov for ov in env_variables if not (ov.envName == env.environment and ov.name == name)]
    env_variables.append(crd.EnvVarOverlay(envName=env.environment, name=name, value=value))
    overlay.envVariables = env_variables
