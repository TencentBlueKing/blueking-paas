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

from paas_wl.release_controller.hooks.models import Command
from paas_wl.utils.constants import CommandStatus, CommandType

pytestmark = pytest.mark.django_db


class TestCommandViewSet:
    @pytest.fixture()
    def hook_maker(self, fake_app, fake_simple_build, bk_user):
        def core(command: str) -> Command:
            return fake_app.command_set.new(
                type_=CommandType.PRE_RELEASE_HOOK,
                operator=bk_user.username,
                build=fake_simple_build,
                command=command,
            )

        return core

    def test_create(self, api_client, fake_app, fake_simple_build, settings):
        url = f"/regions/{settings.FOR_TESTS_DEFAULT_REGION}/apps/{fake_app.name}/commands/"
        data = {
            "type": "pre-release-hook",
            "command": "echo 1;",
            "build": fake_simple_build.uuid,
            "operator": "nobody",
        }
        with mock.patch("paas_wl.resources.tasks.run_command") as run_command:
            resp = api_client.post(url, data=data)

        assert run_command.delay.called
        assert resp.status_code == 201

        pk = resp.json()["uuid"]
        assert Command.objects.get(pk=pk)

    def test_retrieve(self, api_client, fake_app, hook_maker, settings):
        command = hook_maker("echo 1;")
        url = f"/regions/{settings.FOR_TESTS_DEFAULT_REGION}/apps/{fake_app.name}/commands/{command.uuid}"
        resp = api_client.get(url)

        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(command.uuid)

    @pytest.mark.parametrize(
        "status, expected",
        [
            (CommandStatus.FAILED, 400),
            (CommandStatus.SUCCESSFUL, 400),
            (CommandStatus.INTERRUPTED, 400),
            (CommandStatus.SCHEDULED, 200),
            (CommandStatus.PENDING, 200),
        ],
    )
    def test_interrupt_command_x_status(self, api_client, fake_app, hook_maker, settings, status, expected):
        command = hook_maker("echo 1;")
        command.set_logs_was_ready()
        command.update_status(status)

        url = (
            f"/regions/{settings.FOR_TESTS_DEFAULT_REGION}"
            f"/apps/{fake_app.name}/commands/{command.uuid}/interruptions"
        )

        with mock.patch("paas_wl.resources.base.controllers.CommandHandler.interrupt_command"):
            resp = api_client.post(url)

        assert resp.status_code == expected

    def test_interrupt_command_failed(self, api_client, fake_app, hook_maker, settings):
        command = hook_maker("echo 1;")
        command.set_logs_was_ready()
        command.update_status(CommandStatus.SCHEDULED)

        url = (
            f"/regions/{settings.FOR_TESTS_DEFAULT_REGION}"
            f"/apps/{fake_app.name}/commands/{command.uuid}/interruptions"
        )

        with mock.patch(
            "paas_wl.resources.base.controllers.CommandHandler.interrupt_command",
            mock.MagicMock(return_value=False),
        ):
            resp = api_client.post(url)

        assert resp.status_code == 400
        assert resp.json() == {'code': 'INTERRUPTION_FAILED', 'detail': '中断失败: 指令可能已执行完毕.'}
