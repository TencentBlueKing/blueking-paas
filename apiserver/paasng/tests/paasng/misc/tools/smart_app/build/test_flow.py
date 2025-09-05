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

import time
from unittest import mock

import pytest

from paasng.misc.tools.smart_app.build.flow import SmartBuildCoordinator, SmartBuildProcedure
from paasng.misc.tools.smart_app.exceptions import SmartBuildShouldAbortError
from paasng.misc.tools.smart_app.output import ConsoleStream
from paasng.misc.tools.smart_app.phases_steps import SmartBuildPhaseManager
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db


class TestSmartBuildProcedure:
    @pytest.fixture()
    def phases(self, smart_build):
        manager = SmartBuildPhaseManager(smart_build)
        phases = []
        for phase_type in manager.list_phase_types():
            phase = manager.get_or_create(phase_type)
            phases.append(phase)
        return phases

    def test_normal(self, phases):
        stream = ConsoleStream()
        stream.write_title = mock.Mock()  # type: ignore

        with SmartBuildProcedure(stream, None, "doing nothing", phases[0]):
            pass

        assert stream.write_title.call_count == 1
        assert stream.write_title.call_args == ((SmartBuildProcedure.TITLE_PREFIX + "doing nothing",),)

    def test_with_expected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with SmartBuildProcedure(stream, None, "doing nothing", phases[0]):
                raise SmartBuildShouldAbortError("oops")  # noqa: TRY301
        except SmartBuildShouldAbortError:
            pass

        assert stream.write_message.call_count == 1
        assert "oops" in stream.write_message.call_args[0][0]

    def test_with_unexpected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with SmartBuildProcedure(stream, None, "doing nothing", phases[0]):
                raise ValueError("oops")  # noqa: TRY301
        except ValueError:
            pass

        assert stream.write_message.call_count == 1
        # The error message should not contains the original exception message
        assert "oops" not in stream.write_message.call_args[0][0]

    def test_with_smart_build(self, smart_build, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        # 手动标记该阶段的开启, 但 title 未知
        with SmartBuildProcedure(stream, smart_build, "doing nothing", phases[0]) as d:
            assert not d.step_obj

        # title 已知，但是阶段不匹配
        with SmartBuildProcedure(stream, smart_build, "构建 S-Mart 包", phases[0]) as d:
            assert not d.step_obj

        # 正常
        with SmartBuildProcedure(stream, smart_build, "校验应用描述文件", phases[0]) as d:
            assert d.step_obj


class TestSmartBuildCoordinator:
    def test_normal(self, smart_build):
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        assert coordinator.acquire_lock() is True
        assert coordinator.acquire_lock() is False
        coordinator.release_lock()

        # Re-initialize a new object
        smart_build = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        assert coordinator.acquire_lock() is True
        coordinator.release_lock()

    def test_lock_timeout(self, smart_build):
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}", timeout=0.1)
        assert coordinator.acquire_lock() is True
        assert coordinator.acquire_lock() is False

        # wait for lock timeout
        time.sleep(0.2)
        assert coordinator.acquire_lock() is True
        coordinator.release_lock()

    def test_release_without_smart_build(self, smart_build):
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        # Get ongoing smart build
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        assert coordinator.get_current_smart_build() == smart_build
        coordinator.release_lock()
        assert coordinator.get_current_smart_build() is None

    def test_release_with_smart_build(self, smart_build):
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        coordinator.release_lock(smart_build)
        assert coordinator.get_current_smart_build() is None

    def test_release_with_wrong_smart_build(self, smart_build):
        coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")
        coordinator.acquire_lock()
        coordinator.set_smart_build(smart_build)

        new_smart_build = create_fake_smart_build(
            package_name=smart_build.package_name,
            app_code=smart_build.app_code,
            operator=smart_build.operator,
        )
        coordinator = SmartBuildCoordinator(f"{new_smart_build.operator}:{new_smart_build.app_code}")
        with pytest.raises(ValueError, match=r"smart_build lock holder mismatch.*"):
            coordinator.release_lock(new_smart_build)

        assert coordinator.get_current_smart_build() == smart_build

        # 清除 smart_build 的 coordinator
        coordinator.release_lock(smart_build)
