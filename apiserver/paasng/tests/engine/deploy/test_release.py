# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paasng.engine.constants import JobStatus, ReleaseStatus
from paasng.engine.deploy.release import ApplicationReleaseMgr, ReleaseResultHandler
from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.models.managers import DeployPhaseManager
from tests.utils.mocks.engine import mock_cluster_service
from tests.utils.mocks.poll_task import FakeTaskPoller

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    with mock_cluster_service():
        yield


@pytest.fixture
def auto_binding_phases(bk_prod_env, bk_deployment):
    manager = DeployPhaseManager(bk_prod_env)
    phases = manager.get_or_create_all()
    for p in phases:
        manager.attach(DeployPhaseTypes(p.type), bk_deployment)


@pytest.fixture(autouse=True)
def setup_mocks():
    with mock.patch('paasng.engine.deploy.release.ProcessManager'):
        yield


class TestApplicationReleaseMgr:
    """Tests for ApplicationReleaseMgr"""

    def test_failed_when_create_release(self, bk_deployment, auto_binding_phases):
        with mock.patch('paasng.engine.utils.output.RedisChannelStream') as mocked_stream, mock.patch(
            'paasng.engine.deploy.release.update_image_runtime_config'
        ) as mocked_update_image, mock.patch(
            'paasng.engine.deploy.release.EngineDeployClient'
        ) as mocked_client_r, mock.patch(
            'paasng.engine.workflow.flow.EngineDeployClient'
        ):
            mocked_client_r().create_release.side_effect = RuntimeError('can not create release')
            release_mgr = ApplicationReleaseMgr.from_deployment_id(bk_deployment.id)
            release_mgr.start()

            assert mocked_update_image.called
            assert mocked_stream().write_title.called

            # Validate deployment data
            deployment = Deployment.objects.get(pk=bk_deployment.id)
            assert deployment.status == JobStatus.FAILED.value
            assert deployment.err_detail == 'can not create release'

    def test_start_normal(self, bk_deployment, auto_binding_phases):
        with mock.patch('paasng.engine.utils.output.RedisChannelStream'), mock.patch(
            'paasng.engine.deploy.release.EngineDeployClient'
        ) as mocked_client_r, mock.patch('paasng.engine.deploy.release.update_image_runtime_config'), mock.patch(
            'paasng.engine.workflow.flow.EngineDeployClient'
        ), mock.patch(
            'paasng.engine.configurations.ingress.AppDefaultDomains.sync'
        ), mock.patch(
            'paasng.engine.configurations.ingress.AppDefaultSubpaths.sync'
        ):
            faked_release_id = uuid.uuid4().hex
            mocked_client_r().create_release.return_value = mock.Mock(uuid=faked_release_id, version=1)

            release_mgr = ApplicationReleaseMgr.from_deployment_id(bk_deployment.id)
            release_mgr.start()

            deployment = Deployment.objects.get(pk=bk_deployment.id)

            # Validate deployment data
            assert deployment.release_id.hex == faked_release_id
            assert deployment.status == JobStatus.PENDING.value
            assert deployment.err_detail is None


class TestReleaseResultHandler:
    """Tests for ReleaseResultHandler"""

    @pytest.fixture
    def deployment_id(self):
        return str(uuid.uuid4())

    @pytest.mark.parametrize(
        'result,status,error_detail',
        [
            (
                CallbackResult(status=CallbackStatus.EXCEPTION),
                ReleaseStatus.FAILED,
                'Release failed, internal error',
            ),
            (CallbackResult(status=CallbackStatus.NORMAL), ReleaseStatus.SUCCESSFUL, ''),
            (
                CallbackResult(status=CallbackStatus.NORMAL, data={'aborted': False}),
                ReleaseStatus.SUCCESSFUL.value,
                '',
            ),
            (
                # `data` is not a valid AbortedDetails object
                CallbackResult(status=CallbackStatus.NORMAL, data={'aborted': True}),
                ReleaseStatus.SUCCESSFUL,
                '',
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={'aborted': True, 'policy': {'reason': 'foo', 'name': 'foo_policy'}},
                ),
                ReleaseStatus.FAILED,
                'Release aborted, reason: foo',
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={'aborted': True, 'policy': {'reason': 'foo', 'name': 'foo_policy', 'is_interrupted': True}},
                ),
                ReleaseStatus.INTERRUPTED,
                'Release aborted, reason: foo',
            ),
        ],
    )
    def test_failed(self, result, status, error_detail, deployment_id):
        with mock.patch("paasng.engine.deploy.release.ReleaseResultHandler.finish_release") as mocked:
            ReleaseResultHandler().handle(
                result, FakeTaskPoller.create({'extra_params': {'deployment_id': deployment_id}})
            )

        assert mocked.call_count == 1
        assert mocked.call_args[0] == (deployment_id, status, error_detail)
