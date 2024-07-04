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

from paasng.platform.engine.deploy.bg_command.pre_release import ApplicationPreReleaseExecutor
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.utils.output import Style
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models.deploy_config import Hook
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestApplicationPreReleaseExecutor:
    @pytest.fixture()
    def _setup_hook(self, bk_module_full):
        bk_module_full.deploy_hooks.enable_hook(
            type_=DeployHookType.PRE_RELEASE_HOOK, proc_command=generate_random_string()
        )

    @pytest.fixture()
    def _setup_hook_disable(self, bk_module_full, _setup_hook):
        bk_module_full.deploy_hooks.disable_hook(type_=DeployHookType.PRE_RELEASE_HOOK)

    @pytest.fixture()
    def _setup_empty_command_hook(self, bk_module_full):
        bk_module_full.deploy_hooks.enable_hook(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command="")

    @pytest.fixture()
    def hook(self, request, bk_module_full):
        if request.param:
            request.getfixturevalue(request.param)
        return bk_module_full.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)

    @pytest.mark.parametrize("hook", ["_setup_hook_disable", "_setup_empty_command_hook", ""], indirect=["hook"])
    def test_hook_not_found(self, bk_module_full, hook):
        deployment = create_fake_deployment(bk_module_full)
        if not hook or not hook.enabled:
            assert deployment.get_deploy_hooks().get_hook(DeployHookType.PRE_RELEASE_HOOK) is None
        else:
            assert deployment.get_deploy_hooks().get_hook(DeployHookType.PRE_RELEASE_HOOK) == Hook(
                type=hook.type,
                command=hook.get_proc_command(),
                enabled=hook.enabled,
            )

        with mock.patch(
            "paasng.platform.engine.deploy.bg_command.pre_release.ApplicationReleaseMgr"
        ) as mocked_release_mgr, mock.patch("paasng.platform.engine.utils.output.RedisChannelStream") as mocked_stream:
            attach_all_phases(sender=deployment.app_environment, deployment=deployment)
            ApplicationPreReleaseExecutor.from_deployment_id(deployment.pk).start()

        assert mocked_release_mgr.from_deployment_id.called
        assert mocked_release_mgr.from_deployment_id().start.called
        assert mocked_stream().write_message.call_args[0][0] == Style.Warning(
            "The Pre-release command is not configured, skip the Pre-release phase."
        )
