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

"""第三步，由 tasks 里的轮询器驱动：查看一次已提交的部署，结束了就记下结果。

轮询的间隔、总超时和查询出错后的重试都由 blue_krill 的 poll_task 管，这里只管一次查询。只读不写开发者中心，
重复执行没有副作用，记录结果那一步自己保证只生效一次（见 afinish_task）。
"""

import logging
from http import HTTPStatus

import attrs
import httpx2

from app_spark_api.infras.bk_paas import (
    BkPaaSApiError,
    BkPaaSClient,
    BkPaaSUnavailableError,
    DeploymentResult,
    DeploymentStatus,
)
from app_spark_api.publication.constants import MAX_POLLS_FOR_ACCESS_URL, PublicationTaskStatus
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask
from app_spark_api.publication.steps.errors import MSG_DEPLOY_FAILED, MSG_DEPLOY_INTERRUPTED, to_step_error
from app_spark_api.publication.steps.progress import afinish_task

logger = logging.getLogger(__name__)


@attrs.frozen
class PollOutcome:
    """What one look at a deployment found.

    :param finished: 任务是否已经结束（这次记下了结果，或早被别处结束）。
    :param access_url_polls: 部署成功后为等访问地址已经多查的轮数，交给下一轮。
    """

    finished: bool
    access_url_polls: int = 0


async def poll_deployment(task_id: int, client: BkPaaSClient, *, access_url_polls: int = 0) -> PollOutcome:
    """查看一次已提交的部署，结束了就记下任务结果。

    :param access_url_polls: 上一轮带过来的、部署成功后为等访问地址已经多查的轮数。
    """
    # 任务可能已被兜底或删除项目判失败，那就不用再查了。
    task = await PublicationTask.objects.pending().filter(pk=task_id).afirst()
    if task is None:
        return PollOutcome(finished=True)

    binding = await BkPaaSAppBinding.objects.aget(project_id=task.project_id)
    try:
        result = await client.get_deployment_result(
            code=binding.app_code, module=binding.module_name, deployment_id=task.deployment_id
        )
    except (httpx2.HTTPError, BkPaaSUnavailableError, BkPaaSApiError) as exc:
        # 部署在开发者中心照常进行，一次查询失败不代表部署失败。网络问题、服务端错误和限流值得
        # 等下一轮；其余 4xx 说明这次查询本身不成立（如应用已脱离管理），继续查也一样。
        if isinstance(exc, BkPaaSApiError) and not (
            exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or exc.status_code == HTTPStatus.TOO_MANY_REQUESTS
        ):
            await afinish_task(task, PublicationTaskStatus.FAILED, error=to_step_error(exc).message)
            return PollOutcome(finished=True)

        logger.warning("Polling deployment %s failed, will retry: %s", task.deployment_id, exc)
        return PollOutcome(finished=False, access_url_polls=access_url_polls)

    if not result.is_finished:
        return PollOutcome(finished=False, access_url_polls=access_url_polls)

    return await _record_finished_deployment(task, result, access_url_polls)


async def _record_finished_deployment(
    task: PublicationTask, result: DeploymentResult, access_url_polls: int
) -> PollOutcome:
    if result.status == DeploymentStatus.SUCCESSFUL:
        # 成功但还没有访问地址时多查几轮：地址是要分享给同事的，首次发布不能记成空的。
        if not result.access_url and access_url_polls < MAX_POLLS_FOR_ACCESS_URL:
            return PollOutcome(finished=False, access_url_polls=access_url_polls + 1)

        await afinish_task(task, PublicationTaskStatus.SUCCESSFUL, access_url=result.access_url or "")
        return PollOutcome(finished=True)

    error = MSG_DEPLOY_INTERRUPTED if result.status == DeploymentStatus.INTERRUPTED else result.error_detail
    await afinish_task(task, PublicationTaskStatus.FAILED, error=error or MSG_DEPLOY_FAILED)
    return PollOutcome(finished=True)
