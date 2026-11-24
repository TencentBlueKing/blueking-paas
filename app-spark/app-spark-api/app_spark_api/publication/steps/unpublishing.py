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

"""下架的两步：在下架请求里向开发者中心发起下架，之后由 tasks 里的轮询器查看下架结果直到结束。

下架重复发起是安全的：环境已经下架时开发者中心直接返回上一次成功的下架操作，所以发起失败时不用像部署那样
担心「可能已经生效」，记失败让用户再点一次即可。
"""

import logging
from http import HTTPStatus

import httpx2
from django.utils import timezone

from app_spark_api.infras.bk_paas import (
    OFFLINE_ALREADY_IN_PROGRESS_CODE,
    OFFLINE_ENV_NOT_DEPLOYED_CODE,
    BkPaaSApiError,
    BkPaaSClient,
    BkPaaSError,
    BkPaaSUnavailableError,
    OfflineStatus,
)
from app_spark_api.publication.constants import PublicationTaskStatus
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask
from app_spark_api.publication.steps.errors import (
    MSG_UNPUBLISH_ALREADY_RUNNING,
    MSG_UNPUBLISH_FAILED,
    MSG_UNPUBLISH_INTERNAL,
    to_step_error,
)
from app_spark_api.publication.steps.progress import afinish_task

logger = logging.getLogger(__name__)


async def submit_offline(task: PublicationTask, client: BkPaaSClient) -> bool:
    """向开发者中心发起下架；被拒绝或出错时记下任务结果。

    :return: 是否拿到了下架操作 ID；为 True 时由调用方开始轮询。
    """
    try:
        binding = await BkPaaSAppBinding.objects.aget(project_id=task.project_id)
        operation = await client.offline(code=binding.app_code, module=binding.module_name, operator=task.operator)
    except (BkPaaSError, httpx2.HTTPError) as exc:
        await _record_refused_offline(task, exc)
        return False
    except Exception:
        # 数据库抖动这类意外也要当场收场，否则项目要等兜底超时才放开。
        logger.exception("Submitting the offline of publication task %s failed", task.pk)
        await afinish_task(task, PublicationTaskStatus.FAILED, error=MSG_UNPUBLISH_INTERNAL)
        return False

    # 按「仍在进行中」写入：等响应期间任务可能已被兜底或删除项目判失败，那样的任务不再轮询。
    now = timezone.now()
    recorded = (
        await PublicationTask.objects.pending()
        .filter(pk=task.pk)
        .aupdate(offline_operation_id=operation.offline_operation_id, updated_at=now)
    )
    if not recorded:
        return False

    task.offline_operation_id = operation.offline_operation_id
    return True


async def _record_refused_offline(task: PublicationTask, exc: BkPaaSError | httpx2.HTTPError) -> None:
    if isinstance(exc, BkPaaSApiError):
        # 环境从没部署过：开发者中心里本来就没有在运行的东西，和已下架一样，让 AppSpark 的记录跟上。
        if exc.code == OFFLINE_ENV_NOT_DEPLOYED_CODE:
            await afinish_task(task, PublicationTaskStatus.SUCCESSFUL)
            return

        # 开发者中心里刚有人发起了下架：它不给出那次下架的 ID，接不过来。等那次结束后再下架一次，
        # 开发者中心会直接返回它成功的结果。
        if exc.code == OFFLINE_ALREADY_IN_PROGRESS_CODE:
            await afinish_task(task, PublicationTaskStatus.FAILED, error=MSG_UNPUBLISH_ALREADY_RUNNING)
            return

    await afinish_task(task, PublicationTaskStatus.FAILED, error=to_step_error(exc).message)


async def poll_offline(task_id: int, client: BkPaaSClient) -> bool:
    """查看一次下架，结束了就记下任务结果。

    :return: 任务是否已经结束（这次记下了结果，或早被别处结束）。
    """
    # 任务可能已被兜底或删除项目判失败，那就不用再查了。
    task = await PublicationTask.objects.pending().filter(pk=task_id).afirst()
    if task is None:
        return True

    binding = await BkPaaSAppBinding.objects.aget(project_id=task.project_id)
    try:
        result = await client.get_offline_result(
            code=binding.app_code, module=binding.module_name, offline_operation_id=task.offline_operation_id
        )
    except (httpx2.HTTPError, BkPaaSUnavailableError, BkPaaSApiError) as exc:
        # 和查部署结果一样：网络问题、服务端错误和限流等下一轮；其余 4xx 说明这次查询本身不成立，继续查也一样。
        if isinstance(exc, BkPaaSApiError) and not (
            exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or exc.status_code == HTTPStatus.TOO_MANY_REQUESTS
        ):
            await afinish_task(task, PublicationTaskStatus.FAILED, error=to_step_error(exc).message)
            return True

        logger.warning("Polling offline %s failed, will retry: %s", task.offline_operation_id, exc)
        return False

    if not result.is_finished:
        return False

    if result.status == OfflineStatus.SUCCESSFUL:
        await afinish_task(task, PublicationTaskStatus.SUCCESSFUL)
        return True

    await afinish_task(task, PublicationTaskStatus.FAILED, error=result.err_detail or MSG_UNPUBLISH_FAILED)
    return True
