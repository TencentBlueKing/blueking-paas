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
from typing import List, Optional

from pydantic import BaseModel, Field

from paasng.platform.bkapp_model.constants import ResQuotaPlan
from paasng.utils.procfile import generate_bash_command_with_tokens

from .probes import ProbeSet
from .scaling_config import AutoscalingConfig


class Process(BaseModel):
    """
    模块进程

    :param name: 进程名称
    :param command: 进程启动命令
    :param args: 进程启动参数
    :param proc_command: 单行脚本命令, 与 command/args 二选一, 优先于 command/args, 用于设置 Procfile 文件中进程 command
    :param target_port: 监听端口
    :param replicas: 进程副本数. `None` value means the replicas is not specified.
    :param res_quota_plan: 资源配额套餐名
    :param autoscaling: 自动扩缩容配置
    :param probes: 健康检查配置
    """

    name: str

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    proc_command: Optional[str] = None

    target_port: Optional[int] = None

    replicas: Optional[int] = None
    res_quota_plan: Optional[ResQuotaPlan] = None
    autoscaling: Optional[AutoscalingConfig] = None

    probes: Optional[ProbeSet] = None

    def __init__(self, **data):
        data["name"] = data["name"].lower()

        # FIXME 处理 proc_command 与 command/args 的关系
        if proc_command := data.get("proc_command"):
            data["command"] = None
            data["args"] = shlex.split(proc_command)

        super().__init__(**data)

    def get_proc_command(self) -> str:
        """get_proc_command: 生成 Procfile 文件中对应的命令行"""
        if self.proc_command:
            return self.proc_command
        return generate_bash_command_with_tokens(self.command or [], self.args or [])
