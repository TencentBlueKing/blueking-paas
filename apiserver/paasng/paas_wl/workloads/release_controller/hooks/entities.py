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
from dataclasses import dataclass

from attrs import define

from paas_wl.utils.constants import CommandType
from paas_wl.workloads.release_controller.hooks.models import Command as CommandModel


@dataclass
class CommandKubeAdaptor:
    command: CommandModel

    def get_pod_name(self):
        """Get A k8s friendly pod name."""
        if self.command.type == CommandType.PRE_RELEASE_HOOK.value:
            return "pre-release-hook"
        return f"command-{str(self.command.pk)}"


@define
class CommandTemplate:
    """This class declare command which can be used to execute

    :param command: 启动指令
    :param type: 指令类型
    :param build_id: 构建版本 id
    """

    command: str
    type: CommandType
    build_id: str
