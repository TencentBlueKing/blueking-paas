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

"""平台级镜像构建通用任务。

提供 execute_image_build() 通用构建流程函数，各业务模块通过回调注入差异逻辑：
- on_before_build: 构建前的预处理（如 AgentSandbox 需注入 daemon 二进制）
- on_after_success: 构建成功后的后置操作（如 Sidecar 需注册镜像、AgentSandbox 需预拉取）
"""

import logging
from typing import Callable, Optional

from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.platform.image_build.builder import KanikoBuildExecutor
from paasng.platform.image_build.constants import ImageBuildStatus

logger = logging.getLogger(__name__)


def execute_image_build(
    build_id: str,
    *,
    on_before_build: Optional[Callable[[ImageBuildRecord], None]] = None,
    on_after_success: Optional[Callable[[ImageBuildRecord], None]] = None,
) -> None:
    """通用镜像构建执行流程。

    流程：获取记录 → mark_as_building → [on_before_build] → Kaniko 构建 → [on_after_success]

    :param build_id: ImageBuildRecord 的 UUID
    :param on_before_build: 构建前回调，抛异常则标记失败并终止
    :param on_after_success: 构建成功后回调
    """
    try:
        build = ImageBuildRecord.objects.get(uuid=build_id)
    except ImageBuildRecord.DoesNotExist:
        logger.exception("ImageBuildRecord %s not found", build_id)
        return

    # 1. 标记构建中
    build.mark_as_building()

    # 2. 构建前预处理（可选）
    if on_before_build:
        try:
            on_before_build(build)
        except Exception as e:  # noqa: BLE001
            build.mark_as_completed(
                ImageBuildStatus.FAILED,
                build_logs=f"Pre-build step failed: {e}",
            )
            return

    # 3. 执行 Kaniko 构建
    try:
        KanikoBuildExecutor(build).execute()
    except Exception as e:  # noqa: BLE001
        logger.exception("Image build %s failed unexpectedly", build_id)
        build.refresh_from_db()
        if build.status == ImageBuildStatus.BUILDING.value:
            build.mark_as_completed(
                ImageBuildStatus.FAILED,
                build_logs=f"Build failed unexpectedly: {e}",
            )

    # 4. 构建成功后回调（可选）
    build.refresh_from_db()
    if build.status == ImageBuildStatus.SUCCESSFUL.value and on_after_success:
        on_after_success(build)
