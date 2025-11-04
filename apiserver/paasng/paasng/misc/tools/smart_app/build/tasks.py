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

from celery import shared_task
from celery.app.task import Context

from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus
from paasng.utils.i18n.celery import I18nTask

from .builder import SmartAppBuilder
from .flow import SmartBuildStateMgr


@shared_task(base=I18nTask)
def execute_build(
    smart_build_id: str,
    source_get_url: str,
    dest_put_url: str,
    *args,
    **kwargs,
):
    """Execute smart app build task in worker

    :param smart_build_id: Id of smart build object
    :param source_get_url: The source URL to get source code package
    :param dest_put_url: The destination URL to put built artifact
    """

    smart_build = SmartBuildRecord.objects.get(pk=smart_build_id)
    SmartAppBuilder(smart_build, source_get_url, dest_put_url).start()


@shared_task(base=I18nTask)
def execute_build_error_callback(context: Context, exc: Exception, *args, **kwargs):
    """Build task error callback

    :param context: Task context containing the original task request
    :param exc: The exception that was raised
    """

    smart_build_id = context.args[0]
    state_mgr = SmartBuildStateMgr.from_smart_build_id(smart_build_id)
    state_mgr.finish(JobStatus.FAILED, str(exc))
