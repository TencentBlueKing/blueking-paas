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
from paasng.platform.agent_sandbox.image_build.image_cache import prefetch_sandbox_image
from paasng.platform.agent_sandbox.image_build.source_prepare import prepare_source
from paasng.platform.agent_sandbox.models import ImageBuildRecord

logger = logging.getLogger(__name__)


@shared_task()
def run_image_build(build_id: str, prefetch: bool = False):
    """异步执行镜像构建任务。

    :param build_id: ImageBuildRecord 的 UUID
    :param prefetch: 构建成功后是否将镜像预拉取到目标沙箱集群
    """
    try:
        build = ImageBuildRecord.objects.get(uuid=build_id)
    except ImageBuildRecord.DoesNotExist:
        logger.exception("ImageBuildRecord %s not found", build_id)
        return

    # 1. ImageBuildRecord 状态标记为构建中
    build.mark_as_building()

    # 2. 预处理构建包，注入 sandbox daemon 二进制
    try:
        prepare_source(build)
    except Exception as e:  # noqa: BLE001
        build.mark_as_completed(
            ImageBuildStatus.FAILED,
            build_logs=f"Source preparation failed: {e}",
        )
        return

    # 3. 通过 kaniko 方案，构建镜像并完成推送(构建状态会记录到 ImageBuildRecord 中)
    KanikoBuildExecutor(build).execute()

    # 4. 构建成功后，根据 prefetch 参数决定是否预拉取镜像。
    # 预加载的目的是为了加速沙箱启动，失败并不会影响沙箱启动(沙箱启动时，会按照 IfNotPresent 策略尝试拉取)。
    build.refresh_from_db()
    if build.status == ImageBuildStatus.SUCCESSFUL and prefetch:
        prefetch_sandbox_image.delay(build_id)
