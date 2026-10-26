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

import uuid
from unittest import mock

import pytest

from paasng.platform.engine.deploy.interruptions import interrupt_deployment
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


class TestInterruptDeployment:
    @pytest.mark.parametrize(
        ("has_bp_id", "engine_called"),
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

        with mock.patch("paasng.platform.engine.deploy.interruptions.interrupt_build_proc") as mocked_interrupt:
            interrupt_deployment(deployment, bk_user)
            assert mocked_interrupt.called is engine_called

    def test_other_user_allowed(self, bk_module):
        """领域函数不限制中断人，谁能中断由调用方决定：用户态只允许发起人，应用态不限制。"""
        deployment = create_fake_deployment(bk_module)
        interrupt_deployment(deployment, user=create_user())

        deployment.refresh_from_db()
        assert deployment.build_int_requested_at is not None
