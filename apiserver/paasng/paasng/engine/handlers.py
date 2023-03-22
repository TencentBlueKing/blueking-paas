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
import logging
from typing import TYPE_CHECKING

from django.dispatch import receiver
from django.utils import timezone

from paasng.engine.constants import JobStatus
from paasng.engine.models.managers import DeployPhaseManager
from paasng.engine.models.phases import DeployPhaseTypes
from paasng.platform.applications.models import ModuleEnvironment

from .signals import post_appenv_deploy, post_phase_end, pre_appenv_deploy, pre_phase_start

if TYPE_CHECKING:
    from paasng.engine.models import Deployment
    from paasng.engine.workflow import DeployStep as DeployStepMemObj
    from paasng.platform.applications.models import ApplicationEnvironment

logger = logging.getLogger(__name__)


@receiver(pre_phase_start)
def start_phase(sender: 'DeployStepMemObj', phase: DeployPhaseTypes, **kwargs):
    """开启 阶段"""
    phase_obj = sender.deployment.deployphase_set.get(type=phase)
    phase_obj.mark_and_write_to_steam(sender.stream, JobStatus.PENDING)


@receiver(post_phase_end)
def end_phase(sender, status: JobStatus, phase: DeployPhaseTypes, **kwargs):
    """结束 阶段
    :param sender: 需要保证 sender 具备 stream 对象
    :param status: 任务结束状态
    :param phase: 部署所属阶段
    """
    phase_obj = sender.deployment.deployphase_set.get(type=phase)
    phase_obj.mark_and_write_to_steam(sender.stream, status)

    for step in phase_obj.get_unfinished_steps():
        step.mark_and_write_to_steam(sender.stream, status)


@receiver(pre_appenv_deploy)
def attach_all_phases(sender: 'ApplicationEnvironment', deployment: 'Deployment', **kwargs):
    """部署开始，为所有阶段做关联"""
    manager = DeployPhaseManager(deployment.app_environment)
    phases = manager.get_or_create_all()
    for phase in phases:
        is_rebuilt = manager.rebuild_step_if_outdated(phase)
        if is_rebuilt:
            logger.info(
                "steps of engine_app<%s>'s phase<%s> is outdated, rebuilt...",
                deployment.app_environment.engine_app,
                phase.type,
            )
        manager.attach(DeployPhaseTypes(phase.type), deployment)


@receiver(post_appenv_deploy)
def update_last_deployed_date(sender, deployment: 'Deployment', **kwargs):
    """Update module and application's `last_deployed_date` field when a deployment has been finished.

    :param deployment: deployment object.
    """
    env: ModuleEnvironment = deployment.app_environment
    now = timezone.now()
    env.module.last_deployed_date = now
    env.module.save(update_fields=['last_deployed_date'])

    env.application.last_deployed_date = now
    env.application.save(update_fields=['last_deployed_date'])
