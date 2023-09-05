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
import pytest

from paasng.engine.exceptions import NoUnlinkedDeployPhaseError
from paasng.engine.models import DeployPhaseTypes
from paasng.engine.phases_steps.phases import DeployPhaseManager
from tests.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


class TestPhaseManager:
    @pytest.fixture
    def manager(self, bk_stag_env):
        return DeployPhaseManager(bk_stag_env)

    def test_get_or_create(self, bk_stag_env, manager):
        p = manager._get_or_create(phase_type=DeployPhaseTypes.BUILD)
        assert p.type == "build"

        # 不会重复生成
        p2 = manager._get_or_create(phase_type=DeployPhaseTypes.BUILD)
        assert p.pk == p2.pk

    def test_attach(self, bk_stag_env, manager):
        manager.get_or_create_all()
        pp = manager._get_unattached_phase(phase_type=DeployPhaseTypes.PREPARATION)
        assert pp

        manager.attach(
            phase_type=DeployPhaseTypes.PREPARATION,
            deployment=create_fake_deployment(bk_stag_env.module, app_environment="stag"),
        )
        with pytest.raises(NoUnlinkedDeployPhaseError):
            manager._get_unattached_phase(phase_type=DeployPhaseTypes.PREPARATION)

    def test_get_unattached(self, bk_stag_env, manager):
        p1 = manager._get_or_create(phase_type=DeployPhaseTypes.PREPARATION)
        p2 = manager._get_unattached_phase(phase_type=DeployPhaseTypes.PREPARATION)

        assert p1.pk == p2.pk

    def test_rebuild_steps(self):
        """测试步骤变更后重建"""
        # TODO: 仿造 test_steps 构造对应的 step set
