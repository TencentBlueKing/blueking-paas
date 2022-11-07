# -*- coding: utf-8 -*-
from typing import Optional

import pytest

from paas_wl.platform.applications.models.config import Config
from paas_wl.release_controller.hooks.models import Command
from paas_wl.utils.constants import CommandType

pytestmark = pytest.mark.django_db


class TestPreReleaseHook:
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
