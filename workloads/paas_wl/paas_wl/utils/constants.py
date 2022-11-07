# -*- coding: utf-8 -*-
from typing import List

from blue_krill.data_types.enum import EnumField, StructuredEnum


class BuildStatus(str, StructuredEnum):
    SUCCESSFUL = EnumField('successful', '成功')
    FAILED = EnumField('failed', '失败')
    PENDING = EnumField('pending', '等待')
    INTERRUPTED = EnumField('interrupted', '已中断')

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]


class CommandStatus(str, StructuredEnum):
    SCHEDULED = EnumField('scheduled', label="已调度")
    SUCCESSFUL = EnumField('successful', '成功')
    FAILED = EnumField('failed', '失败')
    PENDING = EnumField('pending', '等待')
    INTERRUPTED = EnumField('interrupted', '已中断')

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]


class CommandType(str, StructuredEnum):
    PRE_RELEASE_HOOK = EnumField("pre-release-hook", label="发布前置指令")

    def get_step_name(self):
        if self == CommandType.PRE_RELEASE_HOOK:
            return "pre-release phase"
        else:
            return "command"


def make_enum_choices(obj):
    """Make django field choices form enum"""
    return [(member.value, name) for name, member in obj.__members__.items()]
