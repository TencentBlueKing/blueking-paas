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

"""各步骤共用的任务状态写入：推进阶段、写下结果。都按「仍在进行中」条件更新，已结束的任务不会被改回来。"""

from enum import StrEnum

from django.utils import timezone

from app_spark_api.publication.constants import PublicationStage, PublicationTaskStatus
from app_spark_api.publication.models import PublicationTask
from app_spark_api.publication.steps.errors import MSG_PREPARE_INTERRUPTED, FailureCause, PublicationStepError


class FinishGuard(StrEnum):
    """An extra condition for ending a task judged from a state that may already be stale."""

    # 只在还没发出部署请求时结束，免得判掉刚发出部署请求、正在等响应的任务。
    BEFORE_DEPLOY_REQUEST = "before_deploy_request"
    # 只在还没记下部署 ID 时结束，免得判掉刚拿到部署 ID 的任务。
    BEFORE_DEPLOYMENT_SUBMITTED = "before_deployment_submitted"


async def afinish_task(
    task: PublicationTask,
    status: PublicationTaskStatus,
    *,
    error: str = "",
    access_url: str = "",
    notify: bool = True,
    guard: FinishGuard | None = None,
) -> bool:
    """给仍在进行中的任务写下结果。

    :param notify: 发布面板打开时是否主动展开这条结果。发布请求里创建应用失败时用户当场就看到了，不用再展开。
    :param guard: 兜底按读到的旧状态判失败时，附加的前置条件。
    :return: 是否由这次调用结束了任务；任务早已结束（如另一条轮询抢先记了结果）时为 False。
    """
    now = timezone.now()

    # 按「仍在进行中」更新：并发的两条轮询只有一条能记结果，后到的什么都不改。
    query = PublicationTask.objects.pending().filter(pk=task.pk)
    if guard == FinishGuard.BEFORE_DEPLOY_REQUEST:
        query = query.filter(deploy_requested_at__isnull=True)

    elif guard == FinishGuard.BEFORE_DEPLOYMENT_SUBMITTED:
        query = query.filter(deployment_id="")

    ended = await query.aupdate(
        status=status,
        error=error,
        access_url=access_url,
        result_seen=not notify,
        finished_at=now,
        updated_at=now,
    )
    return bool(ended)


async def afail_task_by_id(task_id: int, error: str) -> None:
    """Fail a pending task known only by its ID, e.g. from a Celery callback."""
    task = await PublicationTask.objects.filter(pk=task_id).afirst()
    if task is not None:
        await afinish_task(task, PublicationTaskStatus.FAILED, error=error)


async def advance_stage(task: PublicationTask, stage: PublicationStage) -> None:
    """把任务推进到下一阶段。

    :raises PublicationStepError: 任务已经结束，调用方应就此停下。
    """
    # 前端轮询发布状态，按 stage 展示进度。按「仍在进行中」写入：打包太慢、已被兜底判失败的任务，
    # 到这里就停下，不再去上传。
    advanced = (
        await PublicationTask.objects.pending().filter(pk=task.pk).aupdate(stage=stage, updated_at=timezone.now())
    )
    if not advanced:
        raise PublicationStepError(MSG_PREPARE_INTERRUPTED, FailureCause.INTERNAL)

    task.stage = stage
