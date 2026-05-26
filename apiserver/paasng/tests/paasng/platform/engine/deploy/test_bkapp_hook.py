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

import pytest
from django.utils import timezone

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.utils.constants import PodPhase
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.bg_command.bkapp_hook import PreReleaseDummyExecutor
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.models.steps import DeployStep
from paasng.platform.engine.utils.output import Style
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _make_hook_handler():
    return mock.MagicMock(
        wait_for_logs_readiness=mock.MagicMock(return_value=PodPhase.RUNNING),
        fetch_logs=mock.MagicMock(return_value=["1", "2"]),
        wait_hook_finished=mock.MagicMock(return_value=PodPhase.SUCCEEDED),
    )


class TestPreReleaseDummyExecutor:
    @pytest.fixture(autouse=True)
    def _setup_wl_app(self, bk_cnative_app, bk_deployment):
        engine_app = bk_deployment.app_environment.engine_app
        WlApp.objects.get_or_create(name=engine_app.name, region=engine_app.region)

    def test_start(self, bk_cnative_app, bk_module, bk_deployment):
        with (
            mock.patch(
                "paasng.platform.engine.deploy.bg_command.bkapp_hook.BkAppHookHandler",
                return_value=_make_hook_handler(),
            ),
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
        ):
            attach_all_phases(sender=bk_deployment.app_environment, deployment=bk_deployment)

            executor = PreReleaseDummyExecutor.from_deployment_id(bk_deployment.id)
            executor.start(generate_random_string())

            assert mocked_stream().write_message.mock_calls == [
                mock.call(Style.Warning("Starting pre-release phase")),
                mock.call("1"),
                mock.call("2"),
                mock.call(Style.Warning("Pre-release execution succeed")),
            ]

    def test_start_interrupted_during_fetch_logs(self, bk_cnative_app, bk_module, bk_deployment):
        # 设置中断标记, 让 _check_release_interrupted 真实返回中断
        bk_deployment.release_int_requested_at = timezone.now()
        bk_deployment.save(update_fields=["release_int_requested_at", "updated"])

        hook_handler = _make_hook_handler()
        with (
            mock.patch(
                "paasng.platform.engine.deploy.bg_command.bkapp_hook.BkAppHookHandler",
                return_value=hook_handler,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.bg_command.bkapp_hook.PreReleaseDummyExecutor._check_release_interrupted",
                side_effect=[(False, 0), (True, 0)],
            ),
            mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream,
        ):
            attach_all_phases(sender=bk_deployment.app_environment, deployment=bk_deployment)

            phase = bk_deployment.deployphase_set.get(type=PreReleaseDummyExecutor.phase_type)
            step, _ = DeployStep.objects.get_or_create(
                phase=phase,
                name=PreReleaseDummyExecutor.step_name,
                defaults={"tenant_id": phase.tenant_id},
            )

            executor = PreReleaseDummyExecutor.from_deployment_id(bk_deployment.id)
            executor.start(generate_random_string())

        # 中断后不应等待 hook 完成
        hook_handler.wait_hook_finished.assert_not_called()
        # 流输出应包含中断提示
        write_calls = mocked_stream().write_message.mock_calls
        assert mock.call(Style.Warning("Pre-release interrupted")) in write_calls

        step.refresh_from_db()
        assert step.status == JobStatus.INTERRUPTED.value
