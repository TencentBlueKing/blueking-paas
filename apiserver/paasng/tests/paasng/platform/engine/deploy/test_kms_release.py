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

from unittest import mock
from unittest.mock import PropertyMock

import pytest

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.processes.entities import SecretFileMount
from paasng.infras.kms.constants import (
    KMS_SECRET_MOUNT_DIR,
    KMS_SECRET_VOLUME_NAME,
    SECRET_KEY_ENVELOPE,
    SECRET_KEY_PRIVATE_KEY,
)
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import Application
from paasng.platform.engine.deploy.release.legacy import _get_extra_envs_and_secret_mounts
from paasng.platform.engine.deploy.release.operator import release_by_k8s_operator
from paasng.platform.engine.exceptions import DeployShouldAbortError

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

LEGACY_MODULE = "paasng.platform.engine.deploy.release.legacy"
OPERATOR_MODULE = "paasng.platform.engine.deploy.release.operator"

KMS_MOUNT = SecretFileMount(
    volume_name=KMS_SECRET_VOLUME_NAME,
    secret_name="kms-res-1",
    mount_dir=KMS_SECRET_MOUNT_DIR,
    sub_paths=(SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY),
)


class TestLegacyExtraEnvsAndSecretMounts:
    """传统 Deployment：敏感变量是否改由 KMS 托管"""

    @pytest.fixture()
    def env(self):
        return mock.Mock(name="env")

    @pytest.fixture()
    def deployment(self):
        return mock.Mock(name="deployment")

    def test_kms_disabled_keeps_encrypted_envs(self, env, deployment):
        with (
            mock.patch(f"{LEGACY_MODULE}.is_kms_injection_enabled", return_value=False),
            mock.patch(f"{LEGACY_MODULE}.get_env_variables", return_value={"DB": "bkpaas_enc$x"}) as get_envs,
            mock.patch(f"{LEGACY_MODULE}.provision_kms_secret") as provision,
        ):
            envs, mounts = _get_extra_envs_and_secret_mounts(env, deployment, from_deploy_flow=True)

        get_envs.assert_called_once_with(env, encrypt_sensitive=True)
        provision.assert_not_called()
        assert envs == {"DB": "bkpaas_enc$x"}
        assert mounts == []

    def test_kms_enabled_requires_deployment(self, env):
        with (
            mock.patch(f"{LEGACY_MODULE}.is_kms_injection_enabled", return_value=True),
            pytest.raises(ValueError, match="部署流程"),
        ):
            _get_extra_envs_and_secret_mounts(env, mock.Mock(), from_deploy_flow=False)

    def test_kms_enabled_splits_sensitive_values(self, env, deployment):
        with (
            mock.patch(f"{LEGACY_MODULE}.is_kms_injection_enabled", return_value=True),
            mock.patch(f"{LEGACY_MODULE}.ensure_kms_injection_supported") as ensure_supported,
            mock.patch(f"{LEGACY_MODULE}.collect_kms_managed_keys", return_value=frozenset({"DB_PASSWORD"})),
            mock.patch(
                f"{LEGACY_MODULE}.get_env_variables",
                return_value={"DB_PASSWORD": "s3cret", "PLAIN": "1"},
            ),
            mock.patch(f"{LEGACY_MODULE}.NamespacesHandler") as ns_handler_cls,
            mock.patch(f"{LEGACY_MODULE}.provision_kms_secret", return_value=KMS_MOUNT) as provision,
        ):
            envs, mounts = _get_extra_envs_and_secret_mounts(env, deployment, from_deploy_flow=True)

        ensure_supported.assert_called_once_with(env)
        ns_handler_cls.new_by_app.return_value.ensure_namespace.assert_called_once_with(env.wl_app.namespace)
        provision.assert_called_once_with(env, deployment, {"DB_PASSWORD": "s3cret"})
        assert envs == {"PLAIN": "1"}
        assert mounts == [KMS_MOUNT]

    def test_kms_enabled_without_sensitive_values_skips_kms(self, env, deployment):
        with (
            mock.patch(f"{LEGACY_MODULE}.is_kms_injection_enabled", return_value=True),
            mock.patch(f"{LEGACY_MODULE}.ensure_kms_injection_supported"),
            mock.patch(f"{LEGACY_MODULE}.collect_kms_managed_keys", return_value=frozenset()),
            mock.patch(f"{LEGACY_MODULE}.get_env_variables", return_value={"PLAIN": "1"}),
            mock.patch(f"{LEGACY_MODULE}.NamespacesHandler") as ns_handler_cls,
            mock.patch(f"{LEGACY_MODULE}.provision_kms_secret") as provision,
        ):
            envs, mounts = _get_extra_envs_and_secret_mounts(env, deployment, from_deploy_flow=True)

        provision.assert_not_called()
        ns_handler_cls.assert_not_called()
        assert envs == {"PLAIN": "1"}
        assert mounts == []


def _sample_bkapp() -> crd.BkAppResource:
    return crd.BkAppResource(
        metadata=ObjectMetadata(name="app"),
        spec=crd.BkAppSpec(
            configuration=crd.BkAppConfiguration(
                env=[crd.EnvVar(name="DB_PASSWORD", value="s3cret"), crd.EnvVar(name="PLAIN", value="1")]
            ),
        ),
    )


@pytest.mark.usefixtures("wl_app")
class TestCloudNativeReleaseWithKMS:
    """云原生应用：敏感变量从 BkApp 中剥离，改由 Secret 文件挂载提供"""

    @pytest.fixture()
    def sensitive_var(self, bk_stag_env, bk_module, config_var_maker):
        config_var_maker(bk_stag_env.environment, bk_module, key="DB_PASSWORD", value="s3cret", is_sensitive=True)

    @pytest.fixture()
    def submitted(self, mocker):
        """替换与集群交互的步骤。返回 apply_bkapp_to_k8s 的 mock，用于检查最终提交的 BkApp"""
        mocker.patch(f"{OPERATOR_MODULE}.get_bkapp_resource_for_deploy", return_value=_sample_bkapp())
        mocker.patch(f"{OPERATOR_MODULE}.AppModelDeploy")
        mocker.patch(f"{OPERATOR_MODULE}.preflight_deploy")
        mocker.patch(f"{OPERATOR_MODULE}.ensure_namespace")
        mocker.patch(f"{OPERATOR_MODULE}.svc_disc")
        mocker.patch(f"{OPERATOR_MODULE}.deploy_addons_tls_certs")
        mocker.patch(f"{OPERATOR_MODULE}.deploy_volume_source")
        mocker.patch(f"{OPERATOR_MODULE}.ensure_bk_log_if_need")
        mocker.patch(f"{OPERATOR_MODULE}.sync_service_monitor")
        mocker.patch(f"{OPERATOR_MODULE}.WaitAppModelReady")
        return mocker.patch(f"{OPERATOR_MODULE}.apply_bkapp_to_k8s", return_value={})

    @pytest.mark.usefixtures("sensitive_var")
    def test_sensitive_values_are_moved_to_secret_mount(self, bk_stag_env, bk_deployment, mocker, submitted):
        bk_stag_env.application.feature_flag.set_feature(AppFeatureFlag.KMS_SECRET_INJECTION, True)
        provision = mocker.patch(f"{OPERATOR_MODULE}.provision_kms_secret", return_value=KMS_MOUNT)

        release_by_k8s_operator(bk_stag_env, mock.Mock(pk=1), "admin", mock.Mock(image="img:1"), bk_deployment)

        provision.assert_called_once_with(bk_stag_env, bk_deployment, {"DB_PASSWORD": "s3cret"})
        deployable = submitted.call_args[0][1]
        assert [var["name"] for var in deployable["spec"]["configuration"]["env"]] == ["PLAIN"]
        assert deployable["spec"]["envOverlay"]["mounts"] == [
            {
                "envName": bk_stag_env.environment,
                "name": KMS_SECRET_VOLUME_NAME,
                "mountPath": KMS_SECRET_MOUNT_DIR,
                "source": {"secret": {"name": "kms-res-1"}},
                "subPaths": [SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY],
            }
        ]

    @pytest.mark.usefixtures("sensitive_var")
    def test_kms_disabled_keeps_env_as_before(self, bk_stag_env, bk_deployment, mocker, submitted):
        provision = mocker.patch(f"{OPERATOR_MODULE}.provision_kms_secret")

        release_by_k8s_operator(bk_stag_env, mock.Mock(pk=1), "admin", mock.Mock(image="img:1"), bk_deployment)

        provision.assert_not_called()
        deployable = submitted.call_args[0][1]
        assert [var["name"] for var in deployable["spec"]["configuration"]["env"]] == ["DB_PASSWORD", "PLAIN"]
        assert "envOverlay" not in deployable["spec"]

    def test_isolated_sandbox_is_rejected_before_any_remote_call(self, bk_stag_env, bk_deployment, mocker, submitted):
        bk_stag_env.application.feature_flag.set_feature(AppFeatureFlag.KMS_SECRET_INJECTION, True)
        mocker.patch.object(Application, "use_isolated_sandbox", new_callable=PropertyMock, return_value=True)
        provision = mocker.patch(f"{OPERATOR_MODULE}.provision_kms_secret")

        with pytest.raises(DeployShouldAbortError):
            release_by_k8s_operator(bk_stag_env, mock.Mock(pk=1), "admin", mock.Mock(image="img:1"), bk_deployment)

        provision.assert_not_called()
        submitted.assert_not_called()
