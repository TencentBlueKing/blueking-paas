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

from celery import shared_task

from paasng.platform.agent_sandbox.image_build.builder import KanikoBuildExecutor
from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.agent_sandbox.image_build.source_prepare import prepare_source
from paasng.platform.agent_sandbox.models import ImageBuildRecord

logger = logging.getLogger(__name__)


@shared_task()
def run_image_build(build_id: str):
    """异步执行镜像构建任务。"""
    try:
        build = ImageBuildRecord.objects.get(uuid=build_id)
    except ImageBuildRecord.DoesNotExist:
        logger.exception("ImageBuildRecord %s not found", build_id)
        return

    build.mark_as_building()

    # 预处理构建包，注入 sandbox daemon 二进制
    try:
        prepare_source(build)
    except Exception:
        logger.exception("Source preparation failed for build %s", build_id)
        build.mark_as_completed(
            ImageBuildStatus.FAILED,
            build_logs="Source preparation failed",
        )
        return

    KanikoBuildExecutor(build).execute()
