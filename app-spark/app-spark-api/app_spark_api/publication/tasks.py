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

"""发布在 Celery 上的两段：准备部署（打包、上传、提交部署），以及轮询部署结果。

准备任务只做一次：重复投递、worker 崩溃后的重投都被 steps.prepare_deployment 的认领挡住，崩溃的那次由查询
发布状态时的兜底判失败。轮询交给 blue_krill 的 poll_task：每轮是一条 Celery 消息，间隔、总超时和出错重试
的进度都随消息带着，不落库。
"""

import logging

from asgiref.sync import async_to_sync
from blue_krill.async_utils.poll_task import (
    CallbackHandler,
    CallbackResult,
    CallbackStatus,
    PollingResult,
    TaskPoller,
)

from app_spark_api.celery import app
from app_spark_api.infras.bk_paas import BkPaaSClient, BkPaaSConfigurationError
from app_spark_api.publication import steps
from app_spark_api.publication.constants import DEPLOY_POLL_INTERVAL_SECONDS, DEPLOY_TIMEOUT, POLL_MAX_RETRIES

logger = logging.getLogger(__name__)


def schedule_deployment_prepare(task_id: int) -> None:
    """投递发布任务的打包、上传和提交部署。

    :raises Exception: 投递失败（如 RabbitMQ 不可用），由调用方决定怎么收场。
    """
    prepare_publication_deployment.apply_async(args=(task_id,))


@app.task(acks_late=True, reject_on_worker_lost=True, ignore_result=True)
def prepare_publication_deployment(task_id: int) -> None:
    """准备并提交一次发布的部署，然后开始轮询。"""
    # 失败都已记成任务失败；连记失败都出错的异常交给 Celery 打日志，不重试，由兜底超时判失败。
    if not async_to_sync(aprepare_once)(task_id):
        return

    # 部署已经提交，投递失败也不能撤回；轮询没起来时，查询发布状态的兜底会在部署超时后判失败。
    try:
        schedule_deployment_poll(task_id)
    except Exception:
        logger.exception("Queueing the first poll of publication task %s failed", task_id)


def schedule_deployment_poll(task_id: int) -> None:
    """开始轮询发布任务的部署结果。

    :raises Exception: 投递失败（如 RabbitMQ 不可用），由调用方决定怎么收场。
    """
    DeploymentPoller.start({"task_id": task_id}, DeploymentPollHandler)


class DeploymentPoller(TaskPoller):
    """Look at a submitted deployment every few seconds until it ends."""

    # 轮询在提交部署后马上开始，总超时从开始轮询算起，就是部署超时。
    overall_timeout_seconds = int(DEPLOY_TIMEOUT.total_seconds())
    default_retry_delay_seconds = DEPLOY_POLL_INTERVAL_SECONDS
    max_retries_on_error = POLL_MAX_RETRIES

    def query(self) -> PollingResult:
        """Look at the deployment once."""
        # 等访问地址的轮数要跨轮累计，放在随消息带到下一轮的数据里。
        last = self.metadata.last_polling_data or {}
        outcome = async_to_sync(apoll_once)(self.params["task_id"], last.get("access_url_polls", 0))
        if outcome.finished:
            return PollingResult.done()

        return PollingResult.doing({"access_url_polls": outcome.access_url_polls})


class DeploymentPollHandler(CallbackHandler):
    """Record why polling gave up; a deployment that ended was already recorded by the poll itself."""

    def handle(self, result: CallbackResult, poller: TaskPoller) -> None:
        """Fail the task when polling timed out or kept erroring."""
        if not result.is_exception:
            return

        if result.status == CallbackStatus.TIMEOUT:
            error = steps.make_deploy_timeout_message()
        else:
            error = steps.MSG_POLL_FAILED

        async_to_sync(steps.afail_task_by_id)(poller.params["task_id"], error)


async def aprepare_once(task_id: int) -> bool:
    """准备部署，返回是否已经提交。"""
    client = await abuild_client_or_fail_task(task_id)
    if client is None:
        return False

    async with client:
        return await steps.prepare_deployment(task_id, client)


async def apoll_once(task_id: int, access_url_polls: int = 0) -> steps.PollOutcome:
    """查看一次部署。"""
    client = await abuild_client_or_fail_task(task_id)
    if client is None:
        return steps.PollOutcome(finished=True)

    async with client:
        return await steps.poll_deployment(task_id, client, access_url_polls=access_url_polls)


async def abuild_client_or_fail_task(task_id: int) -> BkPaaSClient | None:
    """构造开发者中心客户端；本服务没配好对接时把任务判失败。"""
    # 配置错误重试也不会好，当场判失败告诉用户找管理员，而不是让轮询一轮轮重试下去。
    try:
        return BkPaaSClient.from_settings()
    except BkPaaSConfigurationError:
        logger.exception("Publication task %s cannot reach the developer center", task_id)

    await steps.afail_task_by_id(task_id, steps.MSG_NOT_CONFIGURED)
    return None
