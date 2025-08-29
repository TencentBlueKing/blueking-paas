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
from typing import TYPE_CHECKING

from django.dispatch import receiver

from paasng.misc.tools.smart_app.models import SmartBuildPhaseType
from paasng.platform.engine.constants import JobStatus

from .signals import post_phase_end, pre_phase_start

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.workflow import SmartBuildStep as DeployStepMemObj

logger = logging.getLogger(__name__)


@receiver(pre_phase_start)
def start_phase(sender: DeployStepMemObj, phase: SmartBuildPhaseType, **kwargs):
    """开启 阶段"""
    phase_obj = sender.smart_build.smartbuildphase_set.get(type=phase)
    phase_obj.mark_and_write_to_stream(sender.stream, JobStatus.PENDING)


@receiver(post_phase_end)
def end_phase(sender, status: JobStatus, phase: SmartBuildPhaseType, **kwargs):
    """结束 阶段
    :param sender: 需要保证 sender 具备 stream 对象
    :param status: 任务结束状态
    :param phase: 部署所属阶段
    """
    phase_obj = sender.smart_build.smartbuildphase_set.get(type=phase)
    phase_obj.mark_and_write_to_stream(sender.stream, status)

    for step in phase_obj.get_unfinished_steps():
        step.mark_and_write_to_stream(sender.stream, status)
