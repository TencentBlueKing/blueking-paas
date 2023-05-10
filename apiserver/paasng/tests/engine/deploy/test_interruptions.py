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

from paasng.engine.deploy.interruptions import interrupt_deployment
from paasng.engine.exceptions import DeployInterruptionFailed
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


class TestInterruptDeployment:
    @pytest.mark.parametrize(
        'has_bp_id,engine_called',
        [
            (True, True),
            (False, False),
        ],
    )
    def test_build_process_id(self, has_bp_id, engine_called, bk_module, bk_user):
        deployment = create_fake_deployment(bk_module)
        if has_bp_id:
            deployment.build_process_id = str(uuid.uuid4().hex)
            deployment.save()

        with mock.patch('paasng.engine.deploy.interruptions.interrupt_build_proc') as mocked_interrupt:
            interrupt_deployment(deployment, bk_user)
            assert mocked_interrupt.called is engine_called

    def test_failed_incorrect_user(self, bk_module):
        deployment = create_fake_deployment(bk_module)
        with pytest.raises(DeployInterruptionFailed):
            # Use a user different with deployment operator
            interrupt_deployment(deployment, user=create_user())
