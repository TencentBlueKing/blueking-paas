# -*- coding: utf-8 -*-
import datetime
from typing import Optional
from unittest import mock

import pytest
from django.test.utils import override_settings

from paas_wl.platform.applications.models.config import Config
from paas_wl.release_controller.hooks.models import Command
from paas_wl.resources.actions.exec import AppCommandExecutor
from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.utils.kubestatus import HealthStatus, HealthStatusType
from paas_wl.utils.stream import ConsoleStream

pytestmark = pytest.mark.django_db


class TestAppCommandExecutor:
    @pytest.fixture
    def stream(self):
        return ConsoleStream()

    @pytest.fixture()
    def hook_maker(self, fake_app, fake_simple_build, bk_user):
        def core(command: str, config: Optional[Config] = None) -> Command:
            return fake_app.command_set.new(
                type_=CommandType.PRE_RELEASE_HOOK,
                operator=bk_user.username,
                build=fake_simple_build,
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
            "paas_wl.resources.base.controllers.CommandHandler.wait_for_logs_readiness", mock.MagicMock()
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.get_command_logs",
            mock.MagicMock(return_value=["1", "2"]),
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.wait_for_succeeded",
            mock.MagicMock(return_value=None),
        ):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\nexecuting...\n'
            '1\n2\npre-release phase execution succeed.\nCleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.SUCCESSFUL
        assert hook.exit_code == 0

    def test_perform_logs_unready(self, hook_maker, mock_run_command, stream, capsys, caplog):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)
        with mock.patch("paas_wl.resources.actions.exec._WAIT_FOR_READINESS_TIMEOUT", 1):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out
            == 'Starting pre-release phase\nPod is not created normally, please contact the cluster administrator.\n'
            'Cleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.FAILED
        assert hook.exit_code is None

    def test_perform_but_pod_dead(self, hook_maker, mock_run_command, stream, capsys, caplog):
        hook = hook_maker('echo 1;echo 2;')

        executor = AppCommandExecutor(command=hook, stream=stream)
        with mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.wait_for_logs_readiness", mock.MagicMock()
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.get_command_logs",
            mock.MagicMock(return_value=["1", "2"]),
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler._get_pod_status",
            mock.MagicMock(
                return_value=(
                    "Failed",
                    HealthStatus(reason="", message="failed with exit code 1", status=HealthStatusType.UNHEALTHY),
                )
            ),
        ):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\nexecuting...\n'
            '1\n2\nfailed with exit code 1\nCleaning up pre-release phase container\n'
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
            return "Unknown", HealthStatus(
                reason="", message="failed with exit code 1", status=HealthStatusType.UNHEALTHY
            )

        with mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.wait_for_logs_readiness", mock.MagicMock()
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.get_command_logs",
            mock.MagicMock(return_value=["1", "2"]),
        ), mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler._get_pod_status",
            mock.MagicMock(side_effect=interrupt),
        ):
            executor.perform()

        out, err = capsys.readouterr()
        assert (
            out == 'Starting pre-release phase\nexecuting...\n'
            '1\n2\npre-release phase aborted.\nCleaning up pre-release phase container\n'
        )
        assert hook.status == CommandStatus.INTERRUPTED
        assert hook.exit_code == 1
        assert "pre-release phase aborted." in caplog.text
