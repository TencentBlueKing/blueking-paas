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
import pytest
from django.conf import settings

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import AppEnvEncryptionKey, ApplicationFeatureFlag
from paasng.platform.bkapp_model.encryption import (
    CIPHER_PREFIX,
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_NAME,
    apply_encrypted_secret_env_injection,
    collect_sensitive_keys,
    get_or_create_env_encryption_key,
    is_encrypted_secret_env_injection_enabled,
)
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def enable_app_switch(bk_app):
    ApplicationFeatureFlag.objects.set_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION, True, bk_app)


@pytest.fixture()
def disable_app_switch(bk_app):
    # 测试环境全局开关默认开启，新建应用会继承为 True，需显式关闭以构造「应用级关闭」场景
    ApplicationFeatureFlag.objects.set_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION, False, bk_app)


class TestIsEncryptedSecretEnvInjectionEnabled:
    """仅看应用级 feature flag,平台级默认值配置不再参与运行时判定。"""

    def test_app_off(self, bk_stag_env, disable_app_switch):
        assert is_encrypted_secret_env_injection_enabled(bk_stag_env) is False

    def test_app_on(self, bk_stag_env, enable_app_switch):
        assert is_encrypted_secret_env_injection_enabled(bk_stag_env) is True


class TestGetOrCreateRuntimeKey:
    def test_idempotent(self, bk_stag_env):
        key1, _ = get_or_create_env_encryption_key(bk_stag_env, settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE)
        key2, _ = get_or_create_env_encryption_key(bk_stag_env, settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE)
        assert key1 == key2
        assert AppEnvEncryptionKey.objects.filter(application=bk_stag_env.application).count() == 1


class TestCollectSensitiveKeys:
    def test_user_sensitive_vars(self, bk_module, bk_stag_env):
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            is_global=True,
            key="SECRET_TOKEN",
            value="v",
            is_sensitive=True,
            tenant_id=bk_module.tenant_id,
        )
        ConfigVar.objects.create(
            module=bk_module,
            environment=bk_stag_env,
            key="PLAIN_VAR",
            value="v",
            is_sensitive=False,
            tenant_id=bk_module.tenant_id,
        )
        keys = collect_sensitive_keys(bk_stag_env)
        assert "SECRET_TOKEN" in keys
        assert "PLAIN_VAR" not in keys


def _build_resource(env_vars=None, overlay_vars=None) -> crd.BkAppResource:
    spec = crd.BkAppSpec()
    if env_vars:
        spec.configuration.env = [crd.EnvVar(name=k, value=v) for k, v in env_vars]
    if overlay_vars:
        spec.envOverlay = crd.EnvOverlay(
            envVariables=[crd.EnvVarOverlay(envName=e, name=k, value=v) for e, k, v in overlay_vars]
        )
    return crd.BkAppResource(apiVersion="paas.bk.tencent.com/v1alpha2", metadata={"name": "x"}, spec=spec)


def _overlay_env_map(res: crd.BkAppResource, env_name: str) -> dict[str, str]:
    """获取指定 env 的 overlay 环境变量映射。"""
    overlay = res.spec.envOverlay
    if not overlay or not overlay.envVariables:
        return {}
    return {ov.name: ov.value for ov in overlay.envVariables if ov.envName == env_name}


class TestApplyRuntimeEncryption:
    def test_encrypt_and_inject(self, bk_module, bk_stag_env, enable_app_switch):
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            is_global=True,
            key="SECRET_TOKEN",
            value="plain-secret",
            is_sensitive=True,
            tenant_id=bk_module.tenant_id,
        )
        res = _build_resource(
            env_vars=[("SECRET_TOKEN", "plain-secret"), ("PLAIN_VAR", "keepme")],
            overlay_vars=[("stag", "SECRET_TOKEN", "plain-secret"), ("prod", "SECRET_TOKEN", "prod-secret")],
        )
        apply_encrypted_secret_env_injection(res, bk_stag_env)

        env_map = {v.name: v.value for v in res.spec.configuration.env}
        # 密文特有前缀
        assert env_map["SECRET_TOKEN"].startswith(CIPHER_PREFIX)
        assert env_map["PLAIN_VAR"] == "keepme"

    def test_stag_prod_use_different_keys(self, bk_module, bk_stag_env, bk_prod_env, enable_app_switch):
        ConfigVar.objects.create(
            module=bk_module,
            environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
            is_global=True,
            key="SECRET_TOKEN",
            value="plain",
            is_sensitive=True,
            tenant_id=bk_module.tenant_id,
        )
        stag_res = _build_resource(env_vars=[("SECRET_TOKEN", "plain")])
        prod_res = _build_resource(env_vars=[("SECRET_TOKEN", "plain")])
        apply_encrypted_secret_env_injection(stag_res, bk_stag_env)
        apply_encrypted_secret_env_injection(prod_res, bk_prod_env)

        stag_key = _overlay_env_map(stag_res, "stag")[SECRET_KEY_ENV_NAME]
        prod_key = _overlay_env_map(prod_res, "prod")[SECRET_KEY_ENV_NAME]
        assert stag_key != prod_key

    def test_no_sensitive_keys(self, bk_stag_env, enable_app_switch):
        # 只要应用满足开启加密敏感环境变量条件，即使无任何变量被加密，也注入密钥和加密变量名
        res = _build_resource(env_vars=[("PLAIN_VAR", "keepme")])
        apply_encrypted_secret_env_injection(res, bk_stag_env)

        env_map = {v.name: v.value for v in res.spec.configuration.env}
        assert env_map["PLAIN_VAR"] == "keepme"
        # 密钥与清单注入到 overlay
        overlay_map = _overlay_env_map(res, "stag")
        # 双开关开启时，无论是否有变量被加密，统一密钥变量都应注入来标识已开启该功能
        assert SECRET_KEY_ENV_NAME in overlay_map
        # 无敏感变量被加密时，清单变量注入为空串
        assert overlay_map[ENCRYPTED_KEYS_ENV_NAME] == ""

    def test_encrypted_keys_var_lists_only_encrypted(self, bk_module, bk_stag_env, enable_app_switch):
        for key in ("SECRET_A", "SECRET_B"):
            ConfigVar.objects.create(
                module=bk_module,
                environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
                is_global=True,
                key=key,
                value="v",
                is_sensitive=True,
                tenant_id=bk_module.tenant_id,
            )
        res = _build_resource(env_vars=[("SECRET_B", "vb"), ("SECRET_A", "va")])
        apply_encrypted_secret_env_injection(res, bk_stag_env)

        # 清单已排序、逗号分隔，仅含实际加密的 key（注入在 overlay）
        overlay_map = _overlay_env_map(res, "stag")
        assert overlay_map[ENCRYPTED_KEYS_ENV_NAME] == "SECRET_A,SECRET_B"
