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

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class AccessType(int, StructuredEnum):
    """访问方式"""

    WEB = EnumField(0, label=_("网页"))
    API = EnumField(1, label="API")


class ResultCode(int, StructuredEnum):
    """操作结果"""

    SUCCESS = EnumField(0, label=_("成功"))
    ONGOING = EnumField(1, label=_("执行中"))
    FAILURE = EnumField(-1, label=_("失败"))
    INTERRUPT = EnumField(-2, label=_("中断"))

    @classmethod
    def get_terminated_codes(cls):
        return [cls.SUCCESS, cls.FAILURE, cls.INTERRUPT]


class DataType(str, StructuredEnum):
    """记录操作前后数据的数据类型，前端会根据该字段做不同的展示
    前端不需要展示相关的 label, 故不用做国际化标记
    """

    RAW_DATA = EnumField("raw_data", label="原始数据，前端直接渲染即可")
    BKAPP_REVERSION = EnumField("bkapp_revision", label="bkapp.yaml 的版本号，需要通过版本号查询具体的 yaml 内容展示")
    CLOUD_API_RECORD = EnumField(
        "cloud_api_record", label="云 API 权限申请记录 ID, 需要通过 ID 查询具体的申请单据详情展示"
    )


class OperationTarget(str, StructuredEnum):
    """操作对象"""

    APP = EnumField("app", label=_("应用"))
    MODULE = EnumField("module", label=_("模块"))
    PROCESS = EnumField("process", label=_("进程"))
    ACCESS_CONTROL = EnumField("access_control", label=_("用户限制"))
    CLOUD_API = EnumField("cloud_api", label=_("云 API 权限"))
    SECRET = EnumField("secret", label=_("密钥"))
    ENV_VAR = EnumField("env_var", label=_("环境变量"))
    ADD_ON = EnumField("addon", label=_("增强服务"))


class OperationEnum(str, StructuredEnum):
    """操作类型"""

    CREATE = EnumField("create", label=_("新建"))
    DELETE = EnumField("delete", label=_("删除"))
    # 直接操作应用相关的类型，展示的文案包括完整的动宾短语
    CREATE_APP = EnumField("create_app", label=_("创建应用"))
    RELEASE_TO_MARKET = EnumField("online_to_market", label=_("发布到应用市场"))
    OFFLINE_MARKET = EnumField("offline_from_market", label=_("从应用市场下架"))
    MODIFY_MARKET_INFO = EnumField("modify_market_info", label=_("完善应用市场配置"))
    MODIFY_MARKET_URL = EnumField("modify_market_url", label=_("修改应用市场访问地址"))
    MODIFY_BASIC_INFO = EnumField("modify_basic_info", label=_("修改基本信息"))
    # 进程相关操作
    START = EnumField("start", label=_("启动"))
    STOP = EnumField("stop", label=_("停止"))
    SCALE = EnumField("scale", label=_("扩缩容"))
    ENABLE = EnumField("enable", label=_("启用"))
    DISABLE = EnumField("disable", label=_("停用"))
    APPLY = EnumField("apply", label=_("申请"))
    RENEW = EnumField("renew", label=_("续期"))
    DEPLOY = EnumField("deploy", label=_("部署"))
    OFFLINE = EnumField("offline", label=_("下架"))
