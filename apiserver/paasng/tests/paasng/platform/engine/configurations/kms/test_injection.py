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
from paas_wl.bk_app.processes.entities import SecretFileMount
from paasng.platform.engine.configurations.env_var.encryption import (
    CIPHER_PREFIX,
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_VAR_NAME,
)
from paasng.platform.engine.configurations.kms.injection import (
    add_kms_secret_mount,
    collect_kms_managed_keys,
    strip_kms_managed_env_vars,
)
from paasng.platform.engine.exceptions import DeployShouldAbortError


@pytest.mark.django_db(databases=["default", "workloads"])
def test_collect_kms_managed_keys_excludes_unmanaged_builtin_keys(bk_stag_env, mocker):
    mocker.patch(
        "paasng.platform.engine.configurations.kms.injection.collect_sensitive_keys",
        return_value={"DB_PASSWORD", "BKPAAS_APP_SECRET"},
    )

    assert collect_kms_managed_keys(bk_stag_env) == {"DB_PASSWORD"}


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
                ("prod", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", "tok"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"}), "prod": frozenset({"TOKEN"})})

        assert [var.name for var in bkapp.spec.configuration.env] == ["PLAIN"]
        # 覆盖项按各自环境的托管键过滤
        assert _overlay_var_names(bkapp) == [("prod", "DB_PASSWORD")]

    def test_encryption_metadata_removed_when_no_ciphertext_left(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("stag", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("stag", ENCRYPTED_KEYS_ENV_NAME, "DB_PASSWORD"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert _overlay_var_names(bkapp) == []

    def test_encryption_metadata_kept_when_other_ciphertext_remains(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", f"{CIPHER_PREFIX}def"),
                ("prod", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("prod", ENCRYPTED_KEYS_ENV_NAME, "TOKEN"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert _overlay_var_names(bkapp) == [
            ("prod", "TOKEN"),
            ("prod", SECRET_KEY_ENV_VAR_NAME),
            ("prod", ENCRYPTED_KEYS_ENV_NAME),
        ]


KMS_MOUNT = SecretFileMount(
    volume_name="kms-secret", secret_name="kms-res-1", mount_dir="/etc/kms", sub_paths=("envelope", "privateKey")
)


def _user_mount(name: str, mount_path: str, env_name: str | None = None) -> crd.Mount | crd.MountOverlay:
    source = crd.VolumeSource(secret=crd.SecretSource(name="user"))
    if env_name:
        return crd.MountOverlay(envName=env_name, name=name, mountPath=mount_path, source=source)
    return crd.Mount(name=name, mountPath=mount_path, source=source)


class TestAddKMSSecretMount:
    def test_appends_overlay_mount_for_env(self):
        bkapp = _make_bkapp()

        add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)

        assert bkapp.to_deployable()["spec"]["envOverlay"]["mounts"] == [
            {
                "envName": "stag",
                "name": "kms-secret",
                "mountPath": "/etc/kms",
                "source": {"secret": {"name": "kms-res-1"}},
                "subPaths": ["envelope", "privateKey"],
            }
        ]

    @pytest.mark.parametrize(
        ("user_mount", "conflict"),
        [
            (_user_mount("kms-secret", "/data"), True),
            (_user_mount("data", "/etc/kms"), True),
            (_user_mount("data", "/etc/kms/extra"), True),
            (_user_mount("data", "/etc/kms-other"), False),
            (_user_mount("data", "/etc/kms", env_name="stag"), True),
            (_user_mount("kms-secret", "/etc/kms", env_name="prod"), False),
        ],
    )
    def test_conflicts_with_user_mounts(self, user_mount, conflict):
        if isinstance(user_mount, crd.MountOverlay):
            bkapp = _make_bkapp(overlay_mounts=[user_mount])
        else:
            bkapp = _make_bkapp(mounts=[user_mount])

        if conflict:
            with pytest.raises(DeployShouldAbortError):
                add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)
        else:
            add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)
