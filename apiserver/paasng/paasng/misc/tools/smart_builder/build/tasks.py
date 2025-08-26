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
from os import PathLike

from celery import shared_task
from django.dispatch import receiver

from paasng.misc.tools.smart_builder.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_builder.models import SmartBuild
from paasng.misc.tools.smart_builder.signals import post_phase_end, pre_phase_start
from paasng.misc.tools.smart_builder.utils.flow import SmartBuildStateMgr
from paasng.platform.engine.constants import JobStatus
from paasng.utils.i18n.celery import I18nTask

from .builder import SmartAppBuilder

logger = logging.getLogger(__name__)


@shared_task(base=I18nTask)
def dispatch_build(smart_build_id: str, source_package_url: str, package_path: PathLike, *args, **kwargs):
    """Execute smart app build task in worker

    :param smart_build_id: Id of smart build object
    :param source_package_url: The source code repository URL
    :param package_path: The local path of source package file
    """
    smart_build = SmartBuild.objects.get(pk=smart_build_id)
    smart_build_controller = SmartAppBuilder(smart_build, source_package_url, package_path)
    smart_build_controller.start()


@shared_task(base=I18nTask)
def dispatch_build_error_callback(*args, **kwargs):
    context = args[0]
    exc: Exception = args[1]
    # celery.worker.request.Request own property `args` after celery==4.4.0
    smart_build_id: str = context._payload[0][0]

    state_mgr = SmartBuildStateMgr.from_smart_build_id(
        smart_build_id=smart_build_id, phase_type=SmartBuildPhaseType.BUILD
    )
    state_mgr.finish(JobStatus.FAILED, str(exc), write_to_stream=False)


@receiver(pre_phase_start)
def start_phase(sender, phase: SmartBuildPhaseType, **kwargs):
    """开始阶段"""
    phase_obj = sender.smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(sender.stream, JobStatus.PENDING)


@receiver(post_phase_end)
def end_phase(sender, status: JobStatus, phase: SmartBuildPhaseType, **kwargs):
    """结束阶段"""
    phase_obj = sender.smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(sender.stream, status)

    for step in phase_obj.get_unfinished_steps():
        step.mark_and_write_to_stream(sender.stream, status)
