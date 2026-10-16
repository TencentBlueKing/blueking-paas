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

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.engine.configurations.env_var.encryption import (
    encrypt_sensitive_values,
    is_encrypted_secret_env_injection_enabled,
    is_kms_injection_enabled,
)
from paasng.platform.engine.configurations.kms.injection import (
    add_kms_secret_mount,
    ensure_kms_mount_available,
    strip_kms_managed_env_vars,
)
from paasng.platform.engine.exceptions import DeployShouldAbortError


@pytest.mark.django_db(databases=["default", "workloads"])
@pytest.mark.parametrize(
    ("kms_enabled", "app_flag", "expected_kms", "expected_builtin"),
    [
        (True, True, True, False),
        (False, True, False, True),
        (True, False, False, False),
    ],
)
def test_kms_and_builtin_encryption_are_exclusive(
    settings, bk_app, bk_stag_env, kms_enabled, app_flag, expected_kms, expected_builtin
):
    settings.SAAS_KMS_ENABLED = kms_enabled
    bk_app.feature_flag.set_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION, app_flag)

    assert is_kms_injection_enabled(bk_stag_env) is expected_kms
    assert is_encrypted_secret_env_injection_enabled(bk_stag_env) is expected_builtin


@pytest.mark.django_db(databases=["default", "workloads"])
def test_kms_mode_drops_managed_values_instead_of_encrypting(settings, bk_app, bk_stag_env):
    settings.SAAS_KMS_ENABLED = True
    bk_app.feature_flag.set_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION, True)
    values = {"DB_PASSWORD": "s3cret", "BKPAAS_APP_SECRET": "app-secret", "PLAIN": "1"}

    result, encrypted_keys = encrypt_sensitive_values(bk_stag_env, values, {"DB_PASSWORD", "BKPAAS_APP_SECRET"})

    # 写入 BkApp 修订的值不能包含托管的敏感明文
    assert result == {"BKPAAS_APP_SECRET": "app-secret", "PLAIN": "1"}
    assert encrypted_keys == set()


def _make_bkapp(
    env_vars: list[tuple[str, str]] | None = None,
    overlay_vars: list[tuple[str, str, str]] | None = None,
    mounts: list[crd.Mount] | None = None,
    overlay_mounts: list[crd.MountOverlay] | None = None,
) -> crd.BkAppResource:
    """构造只包含配置相关字段的 BkApp。overlay_vars 的每一项为 (envName, name, value)"""
    overlay = None
    if overlay_vars or overlay_mounts:
        overlay = crd.EnvOverlay(
            envVariables=[crd.EnvVarOverlay(envName=e, name=n, value=v) for e, n, v in overlay_vars or []] or None,
            mounts=overlay_mounts,
        )
    return crd.BkAppResource(
        metadata=ObjectMetadata(name="app"),
        spec=crd.BkAppSpec(
            configuration=crd.BkAppConfiguration(env=[crd.EnvVar(name=n, value=v) for n, v in env_vars or []]),
            mounts=mounts,
            envOverlay=overlay,
        ),
    )


def _overlay_var_names(bkapp: crd.BkAppResource) -> list[tuple[str, str]]:
    assert bkapp.spec.envOverlay is not None
    return [(var.envName, var.name) for var in bkapp.spec.envOverlay.envVariables or []]


class TestStripKMSManagedEnvVars:
    def test_removes_managed_keys_from_default_and_overlays(self):
        bkapp = _make_bkapp(
            env_vars=[("DB_PASSWORD", "s3cret"), ("PLAIN", "1")],
            overlay_vars=[
                ("stag", "DB_PASSWORD", "s3cret-stag"),
                ("prod", "DB_PASSWORD", "s3cret-prod"),
                ("prod", "TOKEN", "tok"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"}), "prod": frozenset({"TOKEN"})})

        assert [var.name for var in bkapp.spec.configuration.env] == ["PLAIN"]
        # 覆盖项按各自环境的托管键过滤
        assert _overlay_var_names(bkapp) == [("prod", "DB_PASSWORD")]


KMS_MOUNT = SecretFileMount(
    volume_name="kms-secret", secret_name="kms-res-1", mount_dir="/etc/secrets", sub_paths=("envelope", "private-key")
)


def _user_mount(name: str, mount_path: str, env_name: str | None = None) -> crd.Mount | crd.MountOverlay:
    source = crd.VolumeSource(secret=crd.SecretSource(name="user"))
    if env_name:
        return crd.MountOverlay(envName=env_name, name=name, mountPath=mount_path, source=source)
    return crd.Mount(name=name, mountPath=mount_path, source=source)


class TestKMSSecretMount:
    def test_appends_overlay_mount_for_env(self):
        bkapp = _make_bkapp()

        add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)

        assert bkapp.to_deployable()["spec"]["envOverlay"]["mounts"] == [
            {
                "envName": "stag",
                "name": "kms-secret",
                "mountPath": "/etc/secrets",
                "source": {"secret": {"name": "kms-res-1"}},
                "subPaths": ["envelope", "private-key"],
            }
        ]

        assert bkapp.to_deployable()["spec"]["envOverlay"]["envVariables"] == [
            {"envName": "stag", "name": "BKPAAS_KMS_ENABLED", "value": "true"}
        ]

    @pytest.mark.parametrize(
        ("user_mount", "conflict"),
        [
            (_user_mount("kms-secret", "/data"), True),
            (_user_mount("data", "/etc/secrets"), True),
            (_user_mount("data", "/etc/secrets/extra"), True),
            (_user_mount("data", "/etc/secrets-other"), False),
            (_user_mount("data", "/etc"), True),
            (_user_mount("data", "/"), True),
            (_user_mount("data", "/etc/secrets", env_name="stag"), True),
            (_user_mount("kms-secret", "/etc/secrets", env_name="prod"), False),
        ],
    )
    def test_conflicts_with_user_mounts(self, user_mount, conflict):
        if isinstance(user_mount, crd.MountOverlay):
            bkapp = _make_bkapp(overlay_mounts=[user_mount])
        else:
            bkapp = _make_bkapp(mounts=[user_mount])

        if conflict:
            with pytest.raises(DeployShouldAbortError):
                ensure_kms_mount_available(bkapp, "stag")
        else:
            ensure_kms_mount_available(bkapp, "stag")
