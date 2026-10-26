# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class PermissionApplyStatus(StrStructuredEnum):
    APPROVED = EnumField("approved", label="通过")
    REJECTED = EnumField("rejected", label="驳回")
    PENDING = EnumField("pending", label="待审批")
    CANCELED = EnumField("canceled", label="已取消")


class AlarmRecordStatus(StrStructuredEnum):
    """应用维度告警记录状态"""

    RECEIVED = EnumField("received", label=_("已接收"))
    SKIPPED = EnumField("skipped", label=_("已忽略"))
    SUCCESS = EnumField("success", label=_("告警成功"))
    FAILURE = EnumField("failure", label=_("告警失败"))


# 调用流水日志的最早可回溯天数 (日志保留窗口): time_start 不得早于当前时间前该天数, 边界值允许.
REQUEST_LOG_MAX_LOOKBACK_DAYS = 180
