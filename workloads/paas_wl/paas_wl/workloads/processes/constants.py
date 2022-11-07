# -*- coding: utf-8 -*-
from blue_krill.data_types.enum import EnumField, StructuredEnum

# 注解或标签中存储进程名称的键名
PROCESS_NAME_KEY = "bkapp.paas.bk.tencent.com/process-name"


class AppEnvName(str, StructuredEnum):
    """The default environment names"""

    STAG = EnumField('stag', label="预发布环境")
    PROD = EnumField('prod', label="生产环境")


class ProcessUpdateType(str, StructuredEnum):
    """Type of updating processes"""

    START = EnumField('start')
    STOP = EnumField('stop')
    SCALE = EnumField('scale')


class ProcessTargetStatus(str, StructuredEnum):
    """Choices of process status"""

    START = EnumField('start')
    STOP = EnumField('stop')
