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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class ApprovalServiceName(str, StructuredEnum):
    """审批流程服务名"""

    CREATE_APPROVAL = EnumField("create_approval", label=_("插件上线审批"))
    ONLINE_APPROVAL = EnumField("online_approval", label=_("插件创建审批流程"))
    VISIBLE_RANGE_APPROVAL = EnumField("visible_range_approval", label=_("插件可见范围修改审批流程"))


class ItsmTicketStatus(str, StructuredEnum):
    """ITSM 流程状态"""

    RUNNING = EnumField("RUNNING", label=_("处理中"))
    SUSPENDED = EnumField("SUSPENDED", label=_("被挂起"))
    FINISHED = EnumField("FINISHED", label=_("已结束"))
    # 处理人撤销
    TERMINATED = EnumField("TERMINATED", label=_("被终止"))
    # 申请人撤销
    REVOKED = EnumField("REVOKED", label=_("被撤销"))

    @classmethod
    def completed_status(cls):
        return [cls.FINISHED, cls.TERMINATED, cls.REVOKED]
