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
from abc import ABC, abstractmethod

from .entities import CodeRunResult, ExecResult


class SandboxProcess(ABC):
    """The process operations abstract interface in agent sandbox."""

    @abstractmethod
    def exec(
        self, cmd: list[str] | str, cwd: str | None = None, env: dict | None = None, timeout: int = 60
    ) -> ExecResult:
        """在沙箱中执行命令"""
        raise NotImplementedError

    @abstractmethod
    def code_run(self, content: str, language: str = "Python") -> CodeRunResult:
        """在沙箱中执行脚本"""
        raise NotImplementedError

    @abstractmethod
    def get_logs(self, tail_lines: int | None = None, timestamps: bool = False) -> str:
        """读取容器日志"""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> str:
        """获取 Pod 状态"""
        raise NotImplementedError
