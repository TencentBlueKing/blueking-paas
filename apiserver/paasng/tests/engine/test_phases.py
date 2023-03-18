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
from unittest import mock

import pytest

from paasng.engine.constants import JobStatus
from paasng.engine.models import DeployPhaseTypes
from paasng.engine.models.managers import DeployPhaseManager

pytestmark = pytest.mark.django_db


class TestDeployPhase:
    """测试 DeployPhase"""

    @pytest.fixture
    def engine_app(self, bk_prod_env):
        return bk_prod_env.engine_app

    @pytest.fixture
    def phase_manager(self, bk_prod_env):
        return DeployPhaseManager(bk_prod_env)

    @pytest.fixture
    def preparation_phase(self, phase_manager, engine_app):
        return phase_manager._get_or_create(DeployPhaseTypes.PREPARATION)

    @pytest.mark.parametrize(
        "status, finished", [(JobStatus.PENDING, False), (JobStatus.FAILED, True), (JobStatus.SUCCESSFUL, True)]
    )
    def test_mark(self, preparation_phase, status, finished):
        assert not preparation_phase.status
        assert not preparation_phase.start_time
        assert not preparation_phase.complete_time

        preparation_phase.mark_procedure_status(status)
        assert preparation_phase.status == status
        assert preparation_phase.start_time
        assert bool(preparation_phase.complete_time) == finished

    def test_attach(self, phase_manager, bk_deployment, preparation_phase):
        """测试 deployment 连接"""
        assert not preparation_phase.deployment
        assert not preparation_phase.status
        phase_manager.attach(DeployPhaseTypes.PREPARATION, bk_deployment)
        assert not preparation_phase.status

    @pytest.mark.parametrize(
        "status, extra_info",
        [(JobStatus.FAILED, {}), (JobStatus.FAILED, {"sss": "xxx"}), (JobStatus.SUCCESSFUL, {"sss": "xxx"})],
    )
    def test_mark_and_write_to_steam(self, preparation_phase, status, extra_info):
        with mock.patch('paasng.engine.deploy.infra.output.RedisChannelStream') as mocked_stream:
            preparation_phase.mark_and_write_to_steam(mocked_stream(), status, extra_info)

            assert preparation_phase.status == status.value
            assert mocked_stream().write_event.called

            _a = preparation_phase.to_dict()
            _a.update(extra_info)
            assert mocked_stream().write_event.call_args[0][1] == _a
