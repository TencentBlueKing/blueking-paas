# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paasng.platform.engine.constants import JobStatus, ReleaseStatus
from paasng.platform.engine.deploy.release.legacy import ApplicationReleaseMgr, ReleaseResultHandler
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


@pytest.mark.usefixtures("_auto_binding_phases")
class TestApplicationReleaseMgr:
    """Tests for ApplicationReleaseMgr"""

    def test_failed_when_create_release(self, bk_deployment):
        with mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream, mock.patch(
            "paasng.platform.engine.deploy.release.legacy.update_image_runtime_config"
        ) as mocked_update_image, mock.patch(
            "paasng.platform.engine.deploy.release.legacy.release_to_k8s"
        ) as mocked_create_release, mock.patch("paasng.platform.engine.workflow.flow.EngineDeployClient"), mock.patch(
            "paasng.platform.engine.deploy.release.legacy.ProcessManager"
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
        with mock.patch("paasng.platform.engine.utils.output.RedisChannelStream"), mock.patch(
            "paasng.platform.engine.deploy.release.legacy.release_to_k8s"
        ) as mocked_create_release, mock.patch(
            "paasng.platform.engine.deploy.release.legacy.update_image_runtime_config"
        ), mock.patch("paasng.platform.engine.workflow.flow.EngineDeployClient"), mock.patch(
            "paasng.platform.engine.configurations.ingress.AppDefaultDomains.sync"
        ), mock.patch("paasng.platform.engine.configurations.ingress.AppDefaultSubpaths.sync"), mock.patch(
            "paasng.platform.engine.deploy.release.legacy.ProcessManager"
        ) as fake_process_manager:
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

    def test_sync_specs_from_procfile(self, bk_deployment):
        bk_deployment.procfile = {"web": "start web", "worker": "start worker"}
        bk_deployment.save()
        bk_deployment.refresh_from_db()
        with mock.patch("paasng.platform.engine.utils.output.RedisChannelStream"), mock.patch(
            "paasng.platform.engine.deploy.release.legacy.release_to_k8s"
        ) as mocked_create_release, mock.patch(
            "paasng.platform.engine.deploy.release.legacy.update_image_runtime_config"
        ), mock.patch("paasng.platform.engine.workflow.flow.EngineDeployClient"), mock.patch(
            "paasng.platform.engine.configurations.ingress.AppDefaultDomains.sync"
        ), mock.patch("paasng.platform.engine.configurations.ingress.AppDefaultSubpaths.sync"), mock.patch(
            "paasng.platform.engine.deploy.release.legacy.ProcessManager"
        ) as fake_process_manager:
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
            ProcessTmpl(name="web", command="start web", replicas=None, plan=None),
            ProcessTmpl(name="worker", command="start worker", replicas=None, plan=None),
        ]


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
