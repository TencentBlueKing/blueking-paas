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

import pytest

from paasng.platform.modules.constants import DeployHookType
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestDeployConfig:
    @pytest.fixture()
    def command(self):
        return "one " + generate_random_string()

    @pytest.fixture(autouse=True)
    def setup(self, bk_module, command):
        bk_module.deploy_hooks.upsert(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command=command)

    def test_add_hook(self, bk_module, command):
        hook = bk_module.deploy_hooks.get_by_type(type_=DeployHookType.PRE_RELEASE_HOOK)
        assert hook
        assert hook.type == DeployHookType.PRE_RELEASE_HOOK
        assert hook.get_proc_command() == command
        assert hook.enabled

    def test_disable_hook(self, bk_module, command):
        bk_module.deploy_hooks.disable(type_=DeployHookType.PRE_RELEASE_HOOK)

        hook = bk_module.deploy_hooks.get_by_type(type_=DeployHookType.PRE_RELEASE_HOOK)
        assert hook
        assert hook.type == DeployHookType.PRE_RELEASE_HOOK
        assert hook.get_proc_command() == command
        assert not hook.enabled

    def test_upsert(self, bk_module):
        new_command = "another " + generate_random_string()
        bk_module.deploy_hooks.upsert(type_=DeployHookType.PRE_RELEASE_HOOK, proc_command=new_command)
        hook = bk_module.deploy_hooks.get_by_type(type_=DeployHookType.PRE_RELEASE_HOOK)
        assert hook
        assert hook.type == DeployHookType.PRE_RELEASE_HOOK
        assert hook.get_proc_command() == new_command
        assert hook.enabled
