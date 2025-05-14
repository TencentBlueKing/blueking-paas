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

from typing import List

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

from paasng.platform.engine.constants import JobStatus


class BuildStatus(StrStructuredEnum):
    SUCCESSFUL = EnumField("successful", "成功")
    FAILED = EnumField("failed", "失败")
    PENDING = EnumField("pending", "等待")
    INTERRUPTED = EnumField("interrupted", "已中断")

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]


class CommandStatus(StrStructuredEnum):
    SCHEDULED = EnumField("scheduled", label="已调度")
    SUCCESSFUL = EnumField("successful", "成功")
    FAILED = EnumField("failed", "失败")
    PENDING = EnumField("pending", "等待")
    INTERRUPTED = EnumField("interrupted", "已中断")

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]

    def to_job_status(self) -> JobStatus:
        """Transform to `JobStatus`"""
        # Do type transformation directly because two types are sharing the same
        # members currently.
        if self.value == CommandStatus.SCHEDULED:
            return JobStatus.PENDING
        return JobStatus(self.value)


class CommandType(StrStructuredEnum):
    PRE_RELEASE_HOOK = EnumField("pre-release-hook", label="发布前置指令")

    def get_step_name(self):
        if self == CommandType.PRE_RELEASE_HOOK:
            return "pre-release phase"
        else:
            return "command"

    @classmethod
    def _missing_(cls, value):
        # 兼容 value = pre_release_hook 的场景
        if value == "pre_release_hook":
            return cls.PRE_RELEASE_HOOK
        return super()._missing_(value)


class PodPhase(StrStructuredEnum):
    SUCCEEDED = EnumField("Succeeded", "成功")
    FAILED = EnumField("Failed", "失败")
    RUNNING = EnumField("Running", "运行中")
