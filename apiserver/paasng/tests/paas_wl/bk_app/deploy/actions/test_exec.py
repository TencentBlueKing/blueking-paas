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
import datetime
from typing import Optional
from unittest import mock

import pytest
from django.test.utils import override_settings

from paas_wl.bk_app.deploy.actions.exec import AppCommandExecutor
from paas_wl.bk_app.applications.models.config import Config
from paas_wl.workloads.release_controller.hooks.models import Command
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.utils.kubestatus import HealthStatus, HealthStatusType
from paasng.platform.engine.utils.output import ConsoleStream

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAppCommandExecutor:
    @pytest.fixture
    def stream(self):
        return ConsoleStream()

    @pytest.fixture()
    def hook_maker(self, wl_app, wl_build, bk_user):
        def core(command: str, config: Optional[Config] = None) -> Command:
            return wl_app.command_set.new(
                type_=CommandType.PRE_RELEASE_HOOK,
                operator=bk_user.username,
                build=wl_build,
                command=command,
                config=config,
            )

        return core

    @pytest.fixture(autouse=True)
    def disable_termcolor(self):
        with override_settings(COLORFUL_TERMINAL_OUTPUT=False):
            yield

    def test_perform_successful(self, hook_maker, mock_run_command, stream, capsys):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)
        with mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.wait_for_logs_readiness",
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.get_command_logs", return_value=["1", "2"]
        ), mock.patch("paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.wait_for_succeeded", return_value=None):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\n[TITLE]: executing...\n'
            '1\n2\npre-release phase execution succeed.\n[TITLE]: Cleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.SUCCESSFUL
        assert hook.exit_code == 0

    def test_perform_logs_unready(self, hook_maker, mock_run_command, stream, capsys, caplog):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)
        with mock.patch("paas_wl.bk_app.deploy.actions.exec._WAIT_FOR_READINESS_TIMEOUT", 1):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out
            == 'Starting pre-release phase\nPod is not created normally, please contact the cluster administrator.\n'
            '[TITLE]: Cleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.FAILED
        assert hook.exit_code is None

    def test_perform_but_pod_dead(self, hook_maker, mock_run_command, stream, capsys, caplog):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)
        with mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.wait_for_logs_readiness",
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.get_command_logs", return_value=["1", "2"]
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.command_kmodel.get",
            side_effect=[mock.MagicMock(phase="Pending"), AppEntityNotFound],
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.parse_pod",
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.check_pod_health_status",
            return_value=HealthStatus(reason="", message="failed with exit code 1", status=HealthStatusType.UNHEALTHY),
        ):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\n[TITLE]: executing...\n'
            '1\n2\nfailed with exit code 1\n[TITLE]: Cleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.FAILED
        assert hook.exit_code == 1
        assert f"Pod<{hook.app.namespace}/pre-release-hook> ends unsuccessfully" in caplog.text

    def test_perform_but_be_interrupt(self, hook_maker, mock_run_command, stream, capsys, caplog):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)

        def interrupt(*args, **kwargs):
            hook.int_requested_at = datetime.datetime.now()
            hook.save(update_fields=["int_requested_at", "updated"])
            return HealthStatus(reason="", message="failed with exit code 1", status=HealthStatusType.UNHEALTHY)

        with mock.patch("paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.wait_for_logs_readiness"), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.CommandHandler.get_command_logs", return_value=["1", "2"]
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.command_kmodel.get",
            side_effect=[mock.MagicMock(phase="Pending"), AppEntityNotFound],
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.parse_pod",
        ), mock.patch(
            "paas_wl.bk_app.deploy.app_res.controllers.check_pod_health_status",
            side_effect=interrupt,
        ):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\n[TITLE]: executing...\n'
            '1\n2\npre-release phase aborted.\n[TITLE]: Cleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.INTERRUPTED
        assert hook.exit_code == 1
