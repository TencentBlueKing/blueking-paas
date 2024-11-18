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

import shlex
from typing import Any

from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import Hooks
from paasng.platform.bkapp_model.models import DeployHookType, ModuleDeployHook
from paasng.platform.modules.models import Module
from paasng.utils.structure import NOTSET, NotSetType

from .result import CommonSyncResult


def sync_hooks(
    module: Module, hooks: Hooks | NotSetType | None, manager: fieldmgr.FieldMgrName, use_proc_command: bool = False
) -> CommonSyncResult:
    """Sync hooks data to db model

    :param module: The module object.
    :param hooks: The hooks config.
    :param manager: The field manager performing this action.
    :param use_proc_command: Whether to use "proc_command" field, default is False.
    :return: sync result
    """
    ret = CommonSyncResult()

    field_mgr = fieldmgr.FieldManager(module, fieldmgr.F_HOOKS)
    if not field_mgr.is_managed_by(manager) and hooks == NOTSET:
        return ret

    if not hooks or isinstance(hooks, NotSetType):
        if isinstance(hooks, NotSetType):
            field_mgr.reset()
        ret.deleted_num, _ = ModuleDeployHook.objects.filter(module=module).delete()
        return ret

    # Build the index of existing data first to remove data later.
    # Data structure: {hook type: pk}
    existing_index = {}
    for hook in ModuleDeployHook.objects.filter(module=module):
        existing_index[hook.type] = hook.pk

    # Update or create data
    if pre_release_hook := hooks.pre_release:
        defaults: dict[str, Any]
        if use_proc_command:
            defaults = {
                "proc_command": make_proc_command(pre_release_hook.command, pre_release_hook.args),
            }
        else:
            defaults = {
                "command": pre_release_hook.command,
                "args": pre_release_hook.args,
                "proc_command": None,
            }
        _, created = ModuleDeployHook.objects.update_or_create(
            module=module,
            type=DeployHookType.PRE_RELEASE_HOOK,
            defaults={
                "enabled": True,
            }
            | defaults,
        )
        ret.incr_by_created_flag(created)
        # Move out from the index
        existing_index.pop(DeployHookType.PRE_RELEASE_HOOK, None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ModuleDeployHook.objects.filter(module=module, id__in=existing_index.values()).delete()
    field_mgr.set(manager)
    return ret


def make_proc_command(command: str | list[str] | None, args: list[str] | None) -> str:
    """通过 command/args 构建 Procfile 风格的命令，见 Hook.make_proc_command() 。

    使用场景: 普通应用启动 hook 使用该方法获取启动命令 -> ApplicationPreReleaseExecutor
    """
    if isinstance(command, str):
        return command
    # FIXME: proc_command 并不能简单地通过 shlex.join 合并 command 和 args 生成, 可能出现无法正常运行的问题
    return (shlex.join(command or []) + " " + shlex.join(args or [])).strip()
