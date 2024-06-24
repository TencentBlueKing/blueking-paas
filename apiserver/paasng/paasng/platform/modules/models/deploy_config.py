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
import shlex
from typing import List, Optional, Union

import cattr
from attrs import define
from django.db import models
from jsonfield import JSONField

from paasng.platform.bkapp_model.constants import DEFAULT_SLUG_RUNNER_ENTRYPOINT
from paasng.platform.modules.constants import DeployHookType
from paasng.utils.models import UuidAuditedModel, make_legacy_json_field


@define
class Hook:
    type: DeployHookType
    command: Union[str, List[str]]
    enabled: bool = True
    args: Optional[List[str]] = None

    def get_command(self) -> List[str]:
        """get_args: 获取 hook 的命令部分
        使用场景: 云原生应用构造 manifest 时调用 -> HooksManifestConstructor
        TODO 确认已在 HooksManifestConstructor 中使用?
        """
        if isinstance(self.command, str):
            # TODO: runner 的 Dockerfile 默认的入口程序为 ["/runner/init"], 理论上返回空列表即可
            return DEFAULT_SLUG_RUNNER_ENTRYPOINT
        return self.command

    def get_args(self) -> List[str]:
        """get_args: 获取 hook 的参数部分
        使用场景: 云原生应用构造 manifest 时调用 -> HooksManifestConstructor
        TODO 确认已在 HooksManifestConstructor 中使用?
        """
        if isinstance(self.command, str):
            command = shlex.split(self.command)
            # 有脏数据, 移除前 len(DEFAULT_SLUG_RUNNER_ENTRYPOINT) 个元素
            if self.command.startswith(shlex.join(DEFAULT_SLUG_RUNNER_ENTRYPOINT)):
                return command[len(DEFAULT_SLUG_RUNNER_ENTRYPOINT) :]
            return command
        return self.args or []

    def get_proc_command(self) -> str:
        """get_proc_command: Procfile 风格的命令
        使用场景: 普通应用启动 hook 使用该方法获取启动命令 -> ApplicationPreReleaseExecutor
        """
        if isinstance(self.command, str):
            return self.command
        # Warning: proc_command 并不能简单地通过 shlex.join 合并 command 和 args 生成, 可能出现无法正常运行的问题
        return (shlex.join(self.command or []) + " " + shlex.join(self.args or [])).strip()


class HookList(List[Hook]):
    # warning: 确保 HookList 类型能通过 cattrs 的 is_sequence 判断
    __origin__ = List[Hook]

    def get_hook(self, type_: DeployHookType) -> Optional[Hook]:
        for hook in self:
            if hook.type == type_:
                return hook
        return None

    def upsert(self, type_: DeployHookType, command: Union[str, List[str]], args: Optional[List[str]] = None):
        hook = self.get_hook(type_)
        if hook:
            hook.command = command
            hook.args = args
            hook.enabled = True
        else:
            self.append(Hook(type=type_, command=command, args=args))

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
cattr.register_structure_hook(Union[str, List[str]], lambda items, cl: items)  # type: ignore
cattr.register_unstructure_hook(Union[str, List[str]], lambda value: value)  # type: ignore


# TODO: Replace this models with ModuleProcessSpec && ModuleDeployHook
class DeployConfig(UuidAuditedModel):
    module = models.OneToOneField(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="deploy_config"
    )
    procfile = JSONField(default=dict, help_text="部署命令")
    hooks: HookList = HookListField(help_text="部署钩子", default=HookList)
