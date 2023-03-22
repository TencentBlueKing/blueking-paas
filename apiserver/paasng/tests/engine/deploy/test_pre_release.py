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

from paasng.engine.deploy.pre_release import ApplicationPreReleaseExecutor
from paasng.engine.handlers import attach_all_phases
from paasng.engine.utils.output import Style
from paasng.platform.modules.constants import DeployHookType
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestApplicationPreReleaseExecutor:
    @pytest.fixture
    def deploy_config(self, bk_module_full):
        return bk_module_full.get_deploy_config()

    @pytest.fixture()
    def setup_hook(self, deploy_config):
        deploy_config.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, generate_random_string())
        deploy_config.save()

    @pytest.fixture
    def setup_hook_disable(self, deploy_config, setup_hook):
        deploy_config.hooks.disable(DeployHookType.PRE_RELEASE_HOOK)
        deploy_config.save()

    @pytest.fixture
    def setup_empty_command_hook(self, deploy_config):
        deploy_config.hooks.upsert(DeployHookType.PRE_RELEASE_HOOK, "")
        deploy_config.save()

    @pytest.fixture
    def hook(self, request, deploy_config):
        if request.param:
            request.getfixturevalue(request.param)
        return deploy_config.hooks.get_hook(DeployHookType.PRE_RELEASE_HOOK)

    @pytest.mark.parametrize("hook", ["setup_hook_disable", "setup_empty_command_hook", ""], indirect=["hook"])
    def test_hook_not_found(self, bk_module_full, hook):
        deployment = create_fake_deployment(bk_module_full)
        if hook and not hook.enabled:
            assert deployment.get_deploy_hooks().get_hook(DeployHookType.PRE_RELEASE_HOOK) is None
        else:
            assert deployment.get_deploy_hooks().get_hook(DeployHookType.PRE_RELEASE_HOOK) == hook

        with mock.patch("paasng.engine.deploy.pre_release.ApplicationReleaseMgr") as ApplicationReleaseMgr, mock.patch(
            'paasng.engine.utils.output.RedisChannelStream'
        ) as mocked_stream:
            attach_all_phases(sender=deployment.app_environment, deployment=deployment)
            ApplicationPreReleaseExecutor.from_deployment_id(deployment.pk).start()

        assert ApplicationReleaseMgr.from_deployment_id.called
        assert ApplicationReleaseMgr.from_deployment_id().start.called
        assert mocked_stream().write_message.call_args[0][0] == Style.Warning(
            "The Pre-release command is not configured, skip the Pre-release phase."
        )
