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

from unittest import mock

import pytest

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.utils.constants import PodPhase
from paasng.platform.engine.deploy.bg_command.bkapp_hook import PreReleaseDummyExecutor
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.utils.output import Style
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestPreReleaseDummyExecutor:
    @pytest.fixture(autouse=True)
    def _setup_wl_app(self, bk_cnative_app, bk_deployment):
        name = bk_deployment.app_environment.engine_app.name
        region = bk_deployment.app_environment.engine_app.region
        WlApp.objects.create(name=name, region=region)

    def test_start(self, bk_cnative_app, bk_module, bk_deployment):
        with mock.patch(
            "paasng.platform.engine.deploy.bg_command.bkapp_hook.BkAppHookHandler",
            return_value=mock.MagicMock(
                wait_for_logs_readiness=mock.MagicMock(return_value=PodPhase.RUNNING),
                fetch_logs=mock.MagicMock(return_value=["1", "2"]),
                wait_hook_finished=mock.MagicMock(return_value=PodPhase.SUCCEEDED),
            ),
        ), mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream:
            attach_all_phases(sender=bk_deployment.app_environment, deployment=bk_deployment)

            executor = PreReleaseDummyExecutor.from_deployment_id(bk_deployment.id)
            executor.start(generate_random_string())

            assert mocked_stream().write_message.mock_calls == [
                mock.call(Style.Warning("Starting pre-release phase")),
                mock.call("1"),
                mock.call("2"),
                mock.call(Style.Warning("Pre-release execution succeed")),
            ]
