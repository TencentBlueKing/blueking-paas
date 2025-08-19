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

import logging

from bkpaas_auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from paas_wl.utils.constants import BuildStatus

from .coordinator import SmartBuildCoordinator
from .exceptions import SmartBuildInterruptionFailed
from .models import SmartBuildRecord

logger = logging.getLogger(__name__)


def interrupt_smart_build(smart_build_record: SmartBuildRecord, user: User):
    """中断 smart 包构建"""

    if smart_build_record.operator != user.pk:
        raise SmartBuildInterruptionFailed(_("无法中断由他人发起的 smart 包构建"))
    if smart_build_record.status in BuildStatus.get_finished_states():
        raise SmartBuildInterruptionFailed(_("无法中断, smart 包构建已处于结束状态"))

    now_dt = timezone.now()
    smart_build_record.build_int_requested_at = now_dt
    smart_build_record.save(update_fields=["build_int_requested_at", "updated"])

    # TODO: 现有的只是在每个步骤中间检查用户中断请求，
    # 如果已经进入 pod 构建阶段，由于构建任务已提交至底层容器平台，无法直接取消，
    # 后续可考虑通过与容器平台 API 集成，主动终止相关 pod 或构建任务，以支持更完整的中断功能。
    # 是否添加取消时中止 pod 构建的逻辑?
    coordinator = SmartBuildCoordinator(smart_build_record.signature)
    coordinator.set_interrupted(now_dt.timestamp())
    # 若构建进程的数据上报已经超时，则认为构建失败，主动解锁
    coordinator.release_if_polling_timed_out(expected_smart_build=smart_build_record)
