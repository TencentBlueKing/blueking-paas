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
from blue_krill.encrypt.handler import EncryptHandler
from django.conf import settings

from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import AppEnvEncryptionKey, ApplicationFeatureFlag
from paasng.platform.bkapp_model.encryption import (
    CIPHER_PREFIX,
    collect_sensitive_keys,
    encrypt_sensitive_values,
    get_or_create_env_encryption_key,
    get_runtime_encryption_env_vars,
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


class TestEncryptSensitiveValues:
    def test_encrypts_sensitive_values_and_returns_matching_runtime_metadata(self, bk_stag_env, enable_app_switch):
        values, encrypted_keys = encrypt_sensitive_values(
            bk_stag_env,
            {"SECRET_TOKEN": "plain-secret", "PLAIN_VAR": "keepme"},
            {"SECRET_TOKEN"},
        )

        assert values["SECRET_TOKEN"].startswith(CIPHER_PREFIX)
        assert values["PLAIN_VAR"] == "keepme"
        assert encrypted_keys == {"SECRET_TOKEN"}
        metadata = get_runtime_encryption_env_vars(bk_stag_env, encrypted_keys)
        assert metadata["BKPAAS_ENCRYPTED_ENV_KEYS"] == "SECRET_TOKEN"
        handler = EncryptHandler(
            encrypt_cipher_type=bk_stag_env.get_env_encryption_key().cipher_type,
            secret_key=metadata["BKPAAS_ENCRYPT_SECRET_KEY"],  # type: ignore[arg-type]
        )
        assert handler.decrypt(values["SECRET_TOKEN"].removeprefix(CIPHER_PREFIX)) == "plain-secret"

    def test_uses_existing_key_cipher_type(self, bk_stag_env, enable_app_switch, settings):
        """平台算法配置变更后，已有密钥仍使用创建时记录的算法。"""
        cipher_type = "SM4CTR"
        encryption_key = AppEnvEncryptionKey.objects.create(
            application=bk_stag_env.application,
            environment=bk_stag_env.environment,
            key=AppEnvEncryptionKey.generate_key(cipher_type),
            cipher_type=cipher_type,
            tenant_id=bk_stag_env.application.tenant_id,
        )
        settings.ENCRYPTED_SECRET_ENV_INJECTION_CIPHER_TYPE = "FernetCipher"
        values, _ = encrypt_sensitive_values(bk_stag_env, {"SECRET_TOKEN": "plain-secret"}, {"SECRET_TOKEN"})

        encrypted_value = values["SECRET_TOKEN"]
        assert encrypted_value.startswith(CIPHER_PREFIX)
        handler = EncryptHandler(encrypt_cipher_type=cipher_type, secret_key=encryption_key.key)
        assert handler.decrypt(encrypted_value.removeprefix(CIPHER_PREFIX)) == "plain-secret"

    def test_skips_metadata_when_no_value_is_encrypted(self, bk_stag_env, enable_app_switch):
        values, encrypted_keys = encrypt_sensitive_values(bk_stag_env, {"PLAIN_VAR": "keepme"}, set())

        assert values == {"PLAIN_VAR": "keepme"}
        assert encrypted_keys == set()
        assert get_runtime_encryption_env_vars(bk_stag_env, encrypted_keys) == {}

    def test_skips_encryption_when_feature_is_disabled(self, bk_stag_env, disable_app_switch):
        values, encrypted_keys = encrypt_sensitive_values(
            bk_stag_env, {"SECRET_TOKEN": "plain-secret"}, {"SECRET_TOKEN"}
        )

        assert values == {"SECRET_TOKEN": "plain-secret"}
        assert encrypted_keys == set()
