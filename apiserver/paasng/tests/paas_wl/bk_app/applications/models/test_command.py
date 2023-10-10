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
from typing import Optional

import pytest

from paas_wl.bk_app.applications.models.config import Config
from paas_wl.workloads.release_controller.hooks.models import Command
from paas_wl.utils.constants import CommandType

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestPreReleaseHook:
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

    def test_new(self, hook_maker):
        hook = hook_maker("")
        assert hook.version == 1

    @pytest.mark.parametrize(
        "command, expected",
        [
            ('echo 1', ['echo', '1']),
            ('echo 1;', ['echo', '1;']),
            ('echo "1 2"', ['echo', '1 2']),
            # Bad case, 应该在 serializer 被过滤掉.
            ('echo 1; echo 2;', ['echo', '1;', 'echo', '2;']),
            ('start web', ['start', 'web']),
        ],
    )
    def test_get_command(self, hook_maker, command, expected):
        hook = hook_maker(command=command)
        assert hook.split_command == expected
