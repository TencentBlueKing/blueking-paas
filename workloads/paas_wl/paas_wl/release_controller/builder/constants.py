# -*- coding: utf-8 -*-
from blue_krill.data_types.enum import EnumField, StructuredEnum


class DeployEventStatus(StructuredEnum):
    """部署事件状态"""

    STARTED = EnumField('started', '已开始')
    FINISHED = EnumField('finished', '正常结束')
    ABORTED = EnumField('aborted', '异常结束')
