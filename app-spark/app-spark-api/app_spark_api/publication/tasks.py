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
发布状态时的兜底判失败。轮询每个任务查一次结果，没结束就隔几秒再投递一次自己；只读不写开发者中心，
重复执行没有副作用，记录结果那一步自己保证只生效一次（见 steps.afinish_task）。
"""

import logging

from asgiref.sync import async_to_sync

from app_spark_api.celery import app
from app_spark_api.infras.bk_paas import BkPaaSClient, BkPaaSConfigurationError
from app_spark_api.publication import steps
from app_spark_api.publication.constants import (
    DEPLOY_POLL_INTERVAL_SECONDS,
    POLL_MAX_RETRIES,
    POLL_RETRY_COUNTDOWN_SECONDS,
    PublicationTaskStatus,
)
from app_spark_api.publication.models import PublicationTask

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

    # 部署已经提交，投递失败也不能撤回；查询发布状态时会发现轮询停了，再投递一次。
    try:
        schedule_deployment_poll(task_id, DEPLOY_POLL_INTERVAL_SECONDS)
    except Exception:
        logger.exception("Queueing the first poll of publication task %s failed", task_id)


def schedule_deployment_poll(task_id: int, countdown: float = 0) -> None:
    """投递一次对发布任务部署结果的查询。

    :raises Exception: 投递失败（如 RabbitMQ 不可用），由调用方决定怎么收场。
    """
    poll_publication_deployment.apply_async(args=(task_id,), countdown=countdown)


@app.task(bind=True, acks_late=True, reject_on_worker_lost=True, ignore_result=True, max_retries=POLL_MAX_RETRIES)
def poll_publication_deployment(self, task_id: int) -> None:
    """查看一次发布任务的部署，没结束就再投递下一次查询。"""
    try:
        countdown = async_to_sync(apoll_once)(task_id)
    except Exception as exc:
        # 业务失败已经记成任务失败，到这里的是查询本身出了错（多半是数据库或网络抖动），稍后再查。
        logger.exception("Polling publication task %s failed; retrying", task_id)
        raise self.retry(exc=exc, countdown=POLL_RETRY_COUNTDOWN_SECONDS) from exc

    if countdown is None:
        return

    # 投递失败时不重试：重试本身也要投递。任务会停在原地，查询发布状态时会被重新投递。
    try:
        schedule_deployment_poll(task_id, countdown)
    except Exception:
        logger.exception("Queueing the next poll of publication task %s failed", task_id)


async def aprepare_once(task_id: int) -> bool:
    """准备部署，返回是否已经提交。"""
    client = await abuild_client_or_fail_task(task_id)
    if client is None:
        return False

    async with client:
        return await steps.prepare_deployment(task_id, client)


async def apoll_once(task_id: int) -> float | None:
    """查看一次部署；返回多少秒后再查，任务结束时为 None。"""
    client = await abuild_client_or_fail_task(task_id)
    if client is None:
        return None

    async with client:
        return await steps.poll_deployment(task_id, client)


async def abuild_client_or_fail_task(task_id: int) -> BkPaaSClient | None:
    """构造开发者中心客户端；本服务没配好对接时把任务判失败。"""
    # 配置错误重试也不会好，当场判失败告诉用户找管理员，而不是让轮询一轮轮重试下去。
    try:
        return BkPaaSClient.from_settings()
    except BkPaaSConfigurationError:
        logger.exception("Publication task %s cannot reach the developer center", task_id)

    task = await PublicationTask.objects.filter(pk=task_id).afirst()
    if task is not None:
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.MSG_NOT_CONFIGURED)
    return None
