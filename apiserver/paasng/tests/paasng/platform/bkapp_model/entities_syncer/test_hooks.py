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

import pytest
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import HookCmd, Hooks
from paasng.platform.bkapp_model.entities_syncer import sync_hooks
from paasng.platform.bkapp_model.fieldmgr.constants import FieldMgrName
from paasng.platform.bkapp_model.models import DeployHookType, ModuleDeployHook

pytestmark = pytest.mark.django_db


class Test__sync_hooks:
    def test_create(self, bk_module):
        ret = sync_hooks(bk_module, Hooks(pre_release=HookCmd(command=["foo", "bar"])), FieldMgrName.APP_DESC)
        assert ret.created_num == 1
        assert ModuleDeployHook.objects.filter(module=bk_module).count() == 1
        hook = ModuleDeployHook.objects.get(module=bk_module)
        assert hook.command == ["foo", "bar"]

    def test_update(self, bk_module):
        G(ModuleDeployHook, module=bk_module, type=DeployHookType.PRE_RELEASE_HOOK)
        assert ModuleDeployHook.objects.filter(module=bk_module).count() == 1

        ret = sync_hooks(bk_module, Hooks(pre_release=HookCmd(command=["foo", "bar"])), FieldMgrName.APP_DESC)
        assert ret.updated_num == 1
        assert ModuleDeployHook.objects.filter(module=bk_module).count() == 1
        hook = ModuleDeployHook.objects.get(module=bk_module)
        assert hook.command == ["foo", "bar"]

    def test_delete(self, bk_module):
        G(ModuleDeployHook, module=bk_module, type=DeployHookType.PRE_RELEASE_HOOK)
        assert ModuleDeployHook.objects.filter(module=bk_module).count() == 1

        ret = sync_hooks(bk_module, Hooks(), FieldMgrName.APP_DESC)
        assert ret.deleted_num == 1
        assert ModuleDeployHook.objects.filter(module=bk_module).count() == 0
