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
from typing import List, Optional

import cattr
from attrs import define
from django.db import models
from jsonfield import JSONField

from paasng.platform.modules.constants import DeployHookType
from paasng.utils.models import UuidAuditedModel, make_legacy_json_field


@define
class Hook:
    type: DeployHookType
    command: str
    enabled: bool = True


class HookList(List[Hook]):
    # warning: 确保 HookList 类型能通过 cattrs 的 is_sequence 判断
    __origin__ = List[Hook]

    def get_hook(self, type_: DeployHookType) -> Optional[Hook]:
        for hook in self:
            if hook.type == type_:
                return hook
        return None

    def upsert(self, type_: DeployHookType, command: str):
        hook = self.get_hook(type_)
        if hook:
            hook.command = command
            hook.enabled = True
        else:
            self.append(Hook(type=type_, command=command))

    def disable(self, type_: DeployHookType):
        hook = self.get_hook(type_)
        if hook:
            hook.enabled = False

    @staticmethod
    def __cattrs_structure__(items, cl):
        return cl(cattr.structure(items, List[Hook]))

    @staticmethod
    def __cattrs_unstructure__(value):
        return cattr.unstructure(list(value))


HookListField = make_legacy_json_field("HookListField", HookList)
cattr.register_structure_hook(HookList, HookList.__cattrs_structure__)
cattr.register_unstructure_hook(HookList, HookList.__cattrs_unstructure__)


# TODO: Replace this models with ModuleProcessSpec && ModuleDeployHook
class DeployConfig(UuidAuditedModel):
    module = models.OneToOneField(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name="deploy_config"
    )
    procfile = JSONField(default=dict, help_text="部署命令")
    hooks: HookList = HookListField(help_text="部署钩子", default=HookList)
