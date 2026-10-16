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

import datetime
import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.engine.constants import JobStatus, ReleaseStatus
from paasng.platform.engine.deploy.release.legacy import (
    ApplicationReleaseMgr,
    ReleaseResultHandler,
    release_by_engine,
)
from paasng.platform.engine.deploy.release.operator import BkAppReleaseMgr, release_by_k8s_operator
from paasng.platform.engine.models import Deployment, DeployPhaseTypes
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.engine.phases_steps.phases import DeployPhaseManager
from tests.utils.mocks.poll_task import FakeTaskPoller

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def _auto_binding_phases(bk_prod_env, bk_deployment):
    manager = DeployPhaseManager(bk_prod_env)
    phases = manager.get_or_create_all()
    for p in phases:
        manager.attach(DeployPhaseTypes(p.type), bk_deployment)


@pytest.mark.usefixtures("_with_wl_apps")
@pytest.mark.usefixtures("_auto_binding_phases")
class TestApplicationReleaseMgr:
    """Tests for ApplicationReleaseMgr"""

    def test_failed_when_create_release(self, bk_deployment):
        with (
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
            mock.patch(
                "paasng.platform.engine.deploy.release.legacy.update_image_runtime_config"
            ) as mocked_update_image,
            mock.patch("paasng.platform.engine.deploy.release.legacy.release_to_k8s") as mocked_create_release,
            mock.patch("paasng.platform.engine.workflow.flow.EngineDeployClient"),
            mock.patch("paasng.platform.engine.deploy.release.legacy.ProcessManager"),
        ):
            mocked_create_release.side_effect = RuntimeError("can not create release")
            release_mgr = ApplicationReleaseMgr.from_deployment_id(bk_deployment.id)
            release_mgr.start()

            assert mocked_update_image.called
            assert mocked_stream().write_title.called

            # Validate deployment data
            deployment = Deployment.objects.get(pk=bk_deployment.id)
            assert deployment.status == JobStatus.FAILED.value
            assert deployment.err_detail == "can not create release"

    def test_start_normal(self, bk_deployment):
        bk_deployment.processes = {
            "web": {
                "name": "web",
                "command": "start web",
                "replicas": 2,
            },
            "worker": {"name": "worker", "command": "start worker"},
        }
        bk_deployment.save()
        bk_deployment.refresh_from_db()
        with (
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream"),
            mock.patch("paasng.platform.engine.deploy.release.legacy.release_to_k8s") as mocked_create_release,
            mock.patch("paasng.platform.engine.deploy.release.legacy.update_image_runtime_config"),
            mock.patch("paasng.platform.engine.workflow.flow.EngineDeployClient"),
            mock.patch("paasng.platform.engine.configurations.ingress.AppDefaultDomains.sync"),
            mock.patch("paasng.platform.engine.configurations.ingress.AppDefaultSubpaths.sync"),
            mock.patch("paasng.platform.engine.deploy.release.legacy.ProcessManager") as fake_process_manager,
        ):
            faked_release_id = uuid.uuid4().hex
            mocked_create_release.return_value = mock.Mock(uuid=faked_release_id, version=1)

            release_mgr = ApplicationReleaseMgr.from_deployment_id(bk_deployment.id)
            release_mgr.start()

        # Validate deployment data
        deployment = Deployment.objects.get(pk=bk_deployment.id)
        assert deployment.release_id.hex == faked_release_id
        assert deployment.status == JobStatus.PENDING.value
        assert deployment.err_detail is None

        # Validate sync specs data
        assert fake_process_manager().sync_processes_specs.called
        (processes,) = fake_process_manager().sync_processes_specs.call_args[0]
        assert processes == [
            ProcessTmpl(name="web", command="start web", replicas=2, plan=None),
            ProcessTmpl(name="worker", command="start worker", replicas=None, plan=None),
        ]

    def test_interrupted(self, bk_deployment):
        Deployment.objects.filter(pk=bk_deployment.id).update(
            release_int_requested_at=datetime.datetime.now(), build_int_requested_at=datetime.datetime.now()
        )

        release_mgr = ApplicationReleaseMgr.from_deployment_id(bk_deployment.id)
        release_mgr.start()

        assert Deployment.objects.get(pk=bk_deployment.id).status == JobStatus.INTERRUPTED


@pytest.mark.usefixtures("_auto_binding_phases")
class TestBkAppReleaseMgr:
    def test_interrupted(self, bk_deployment):
        Deployment.objects.filter(pk=bk_deployment.id).update(
            release_int_requested_at=datetime.datetime.now(), build_int_requested_at=datetime.datetime.now()
        )

        release_mgr = BkAppReleaseMgr.from_deployment_id(bk_deployment.id)
        release_mgr.start()

        assert Deployment.objects.get(pk=bk_deployment.id).status == JobStatus.INTERRUPTED


@pytest.mark.usefixtures("_with_wl_apps")
class TestKMSRelease:
    @pytest.fixture()
    def kms_mount(self, settings, bk_app) -> SecretFileMount:
        """开启应用的 KMS 托管，并提供已就绪的 Secret 挂载。"""
        settings.SAAS_KMS_ENABLED = True
        bk_app.feature_flag.set_feature(AppFeatureFlag.ENCRYPTED_SECRET_ENV_INJECTION, True)
        return SecretFileMount(
            volume_name="kms-secret",
            secret_name="kms-test",
            mount_dir="/etc/secrets",
            sub_paths=("envelope", "privateKey"),
        )

    def test_legacy_release_strips_password_and_waits_for_secret(self, bk_deployment, kms_mount):
        """普通应用先准备 namespace 和 Secret，再以普通变量及文件挂载发起发布。"""
        env = bk_deployment.app_environment
        calls = mock.Mock()
        calls.provision.return_value = kms_mount
        calls.release.return_value = mock.Mock(uuid=uuid.uuid4(), version=1)
        injection_path = "paasng.platform.engine.configurations.kms.injection"
        release_path = "paasng.platform.engine.deploy.release.legacy"
        with (
            mock.patch(f"{injection_path}.collect_sensitive_keys", return_value={"DB_PASSWORD"}),
            mock.patch(f"{injection_path}.get_env_variables", return_value={"DB_PASSWORD": "secret", "PLAIN": "1"}),
            mock.patch(f"{injection_path}.NamespacesHandler.new_by_app") as namespace_handler,
            mock.patch(f"{injection_path}.provision_kms_secret", calls.provision),
            mock.patch(f"{release_path}.release_to_k8s", calls.release),
            mock.patch(f"{release_path}.wait_for_release"),
        ):
            namespace_handler.return_value.ensure_namespace = calls.ensure_namespace
            release_by_engine(env, "build-id", deployment=bk_deployment)

        assert calls.mock_calls[:3] == [
            mock.call.ensure_namespace(env.wl_app.namespace),
            mock.call.provision(env, bk_deployment, {"DB_PASSWORD": "secret"}),
            mock.call.release(
                env,
                "build-id",
                {"PLAIN": "1", "BKPAAS_KMS_ENABLED": "true"},
                bk_deployment.get_procfile(),
                secret_mounts=[kms_mount],
            ),
        ]

    def test_operator_release_strips_password_and_waits_for_secret(self, bk_deployment, kms_mount):
        """云原生发布提交前剥离敏感变量，并在 namespace 和 Secret 就绪后追加挂载。"""
        env = bk_deployment.app_environment
        bkapp = crd.BkAppResource(
            metadata=ObjectMetadata(name="app"),
            spec=crd.BkAppSpec(
                configuration=crd.BkAppConfiguration(
                    env=[crd.EnvVar(name="DB_PASSWORD", value="secret"), crd.EnvVar(name="PLAIN", value="1")]
                )
            ),
        )
        calls = mock.Mock()
        calls.provision.return_value = kms_mount
        calls.submit.return_value = {"kind": "BkApp"}
        revision = mock.Mock(pk=1)
        module_path = "paasng.platform.engine.deploy.release.operator"
        with (
            mock.patch(f"{module_path}.AppModelDeploy.objects.create", return_value=mock.Mock(id=1)),
            mock.patch(f"{module_path}.get_bkapp_resource_for_deploy", return_value=bkapp),
            mock.patch(
                f"{module_path}.collect_kms_managed_keys_by_env",
                return_value={env.environment: frozenset({"DB_PASSWORD"})},
            ),
            mock.patch(
                "paasng.platform.engine.configurations.kms.injection.get_env_variables",
                return_value={"DB_PASSWORD": "secret", "PLAIN": "1"},
            ),
            mock.patch(f"{module_path}.preflight_deploy"),
            mock.patch(f"{module_path}.ensure_namespace", calls.ensure_namespace),
            mock.patch(f"{module_path}.provision_kms_secret", calls.provision),
            mock.patch(f"{module_path}.svc_disc.apply_configmap"),
            mock.patch(f"{module_path}.deploy_addons_tls_certs"),
            mock.patch(f"{module_path}.deploy_volume_source"),
            mock.patch(f"{module_path}.apply_bkapp_to_k8s", calls.submit),
            mock.patch(f"{module_path}.ensure_bk_log_if_need"),
            mock.patch(f"{module_path}.sync_service_monitor"),
            mock.patch(f"{module_path}.WaitAppModelReady.start"),
        ):
            release_by_k8s_operator(env, revision, "tester", mock.Mock(image="test:latest"), bk_deployment)

        submitted = calls.submit.call_args.args[1]
        assert calls.mock_calls[:3] == [
            mock.call.ensure_namespace(env),
            mock.call.provision(env, bk_deployment, {"DB_PASSWORD": "secret"}),
            mock.call.submit(env, submitted),
        ]
        assert submitted["spec"]["configuration"]["env"] == [{"name": "PLAIN", "value": "1"}]
        overlay = submitted["spec"]["envOverlay"]
        assert overlay["mounts"][0]["source"] == {"secret": {"name": "kms-test"}}
        assert overlay["mounts"][0]["subPaths"] == ["envelope", "privateKey"]
        assert overlay["envVariables"] == [{"envName": env.environment, "name": "BKPAAS_KMS_ENABLED", "value": "true"}]


class TestReleaseResultHandler:
    """Tests for ReleaseResultHandler"""

    @pytest.fixture()
    def deployment_id(self):
        return str(uuid.uuid4())

    @pytest.mark.parametrize(
        ("result", "status", "error_detail"),
        [
            (
                CallbackResult(status=CallbackStatus.EXCEPTION),
                ReleaseStatus.FAILED,
                "Release failed, internal error",
            ),
            (CallbackResult(status=CallbackStatus.NORMAL), ReleaseStatus.SUCCESSFUL, ""),
            (
                CallbackResult(status=CallbackStatus.NORMAL, data={"aborted": False}),
                ReleaseStatus.SUCCESSFUL.value,
                "",
            ),
            (
                # `data` is not a valid AbortedDetails object
                CallbackResult(status=CallbackStatus.NORMAL, data={"aborted": True}),
                ReleaseStatus.SUCCESSFUL,
                "",
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={"aborted": True, "policy": {"reason": "foo", "name": "foo_policy"}},
                ),
                ReleaseStatus.FAILED,
                "Release aborted, reason: foo",
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={"aborted": True, "policy": {"reason": "foo", "name": "foo_policy", "is_interrupted": True}},
                ),
                ReleaseStatus.INTERRUPTED,
                "Release aborted, reason: foo",
            ),
        ],
    )
    def test_failed(self, result, status, error_detail, deployment_id):
        with mock.patch("paasng.platform.engine.deploy.release.legacy.ReleaseResultHandler.finish_release") as mocked:
            ReleaseResultHandler().handle(
                result, FakeTaskPoller.create({"extra_params": {"deployment_id": deployment_id}})
            )

        assert mocked.call_count == 1
        assert mocked.call_args[0] == (deployment_id, status, error_detail)
