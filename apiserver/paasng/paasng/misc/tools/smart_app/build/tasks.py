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
from typing import Any

from celery import shared_task
from celery.worker.request import Request

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus
from paasng.utils.i18n.celery import I18nTask

from .builder import SmartAppBuilder
from .flow import SmartBuildStateMgr

logger = logging.getLogger(__name__)


@shared_task(base=I18nTask)
def execute_build(smart_build_id: str, source_package_url: str, package_path: PathLike, *args, **kwargs):
    """Execute smart app build task in worker

    :param smart_build_id: Id of smart build object
    :param source_package_url: The source code repository URL
    :param package_path: The local path of source package file
    """
    smart_build = SmartBuildRecord.objects.get(pk=smart_build_id)
    builder = SmartAppBuilder(smart_build, source_package_url, package_path)
    builder.start()


@shared_task(base=I18nTask)
def execute_build_error_callback(context: Request, exc: Exception, traceback: Any, task_id: str):
    """Callback function for handling build task failure

    :param context: Celery task request context, which contains info related to task execution
    :param exc: Exception object thrown during the construction process
    :param traceback: Exception traceback information
    :param task_id: The unique identifier of the failed task
    """
    # celery.worker.request.Request own property `args` after celery==4.4.0
    smart_build_id: str = context._payload[0][0]

    logger.error("Smart app build failed for build_id=%s, task_id=%s, error=%s", smart_build_id, task_id, str(exc))

    state_mgr = SmartBuildStateMgr.from_smart_build_id(
        smart_build_id=smart_build_id, phase_type=SmartBuildPhaseType.BUILD
    )
    state_mgr.finish(JobStatus.FAILED, str(exc), write_to_stream=False)
