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
import time
from unittest import mock

import pytest

from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import DeployPhaseTypes
from paasng.platform.engine.phases_steps.phases import DeployPhaseManager
from paasng.platform.engine.utils.output import ConsoleStream
from paasng.platform.engine.workflow.flow import DeploymentCoordinator, DeployProcedure
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    with mock_cluster_service():
        yield


class TestDeployProcedure:
    @pytest.fixture
    def phases(self, bk_prod_env, bk_deployment):
        manager = DeployPhaseManager(bk_prod_env)
        phases = manager.get_or_create_all()
        for p in phases:
            manager.attach(DeployPhaseTypes(p.type), bk_deployment)
        return phases

    def test_normal(self, phases):
        stream = ConsoleStream()
        stream.write_title = mock.Mock()  # type: ignore

        with DeployProcedure(stream, None, 'doing nothing', phases[0]):
            pass

        assert stream.write_title.call_count == 1
        assert stream.write_title.call_args == ((DeployProcedure.TITLE_PREFIX + 'doing nothing',),)

    def test_with_expected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with DeployProcedure(stream, None, 'doing nothing', phases[0]):
                raise DeployShouldAbortError('oops')
        except DeployShouldAbortError:
            pass

        assert stream.write_message.call_count == 1
        assert stream.write_message.call_args[0][0].endswith('oops。')

    def test_with_unexpected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with DeployProcedure(stream, None, 'doing nothing', phases[0]):
                raise ValueError('oops')
        except ValueError:
            pass

        assert stream.write_message.call_count == 1
        # The error message should not contains the original exception message
        assert 'oops' not in stream.write_message.call_args[0][0]

    def test_with_deployment(self, bk_deployment, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        # 手动标记该阶段的开启, 但 title 未知
        with DeployProcedure(stream, bk_deployment, 'doing nothing', phases[0]) as d:
            assert not d.step_obj

        # title 已知，但是阶段不匹配
        with DeployProcedure(stream, bk_deployment, '检测部署结果', phases[0]) as d:
            assert not d.step_obj

        # 正常
        with DeployProcedure(stream, bk_deployment, '配置资源实例', phases[0]) as d:
            assert d.step_obj


class TestDeploymentCoordinator:
    def test_normal(self, bk_stag_env):
        env_mgr = DeploymentCoordinator(bk_stag_env)
        assert env_mgr.acquire_lock() is True
        assert env_mgr.acquire_lock() is False
        env_mgr.release_lock()

        # Re-initialize a new object
        env_mgr = DeploymentCoordinator(bk_stag_env)
        assert env_mgr.acquire_lock() is True
        env_mgr.release_lock()

    def test_lock_timeout(self, bk_stag_env):
        env_mgr = DeploymentCoordinator(bk_stag_env, timeout=0.1)
        assert env_mgr.acquire_lock() is True
        assert env_mgr.acquire_lock() is False

        # wait for lock timeout
        time.sleep(0.2)
        assert env_mgr.acquire_lock() is True
        env_mgr.release_lock()

    def test_release_without_deployment(self, bk_deployment, bk_stag_env):
        env_mgr = DeploymentCoordinator(bk_stag_env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(bk_deployment)

        # Get ongoing deployment
        env_mgr = DeploymentCoordinator(bk_stag_env)
        assert env_mgr.get_current_deployment() == bk_deployment
        env_mgr.release_lock()
        assert env_mgr.get_current_deployment() is None

    def test_release_with_deployment(self, bk_deployment, bk_stag_env):
        env_mgr = DeploymentCoordinator(bk_stag_env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(bk_deployment)

        env_mgr = DeploymentCoordinator(bk_stag_env)
        env_mgr.release_lock(bk_deployment)
        assert env_mgr.get_current_deployment() is None

    def test_release_with_wrong_deployment(self, bk_deployment, bk_stag_env, bk_module):
        env_mgr = DeploymentCoordinator(bk_stag_env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(bk_deployment)

        deployment = create_fake_deployment(bk_module)
        env_mgr = DeploymentCoordinator(bk_stag_env)
        with pytest.raises(ValueError):
            env_mgr.release_lock(deployment)

        assert env_mgr.get_current_deployment() == bk_deployment
