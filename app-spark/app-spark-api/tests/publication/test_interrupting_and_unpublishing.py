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

"""The owner interrupts a running deployment or unpublishes the Project; the state follows the developer center."""

import pytest
from django.utils import timezone

from app_spark_api.infras.bk_paas import (
    OFFLINE_ALREADY_IN_PROGRESS_CODE,
    OFFLINE_ENV_NOT_DEPLOYED_CODE,
    BkPaaSApiError,
    DeploymentResult,
)
from app_spark_api.publication import services, steps
from app_spark_api.publication.constants import PublicationTaskStatus
from app_spark_api.publication.exceptions import PublicationInterruptConflictError
from app_spark_api.publication.models import PublicationTask

pytestmark = pytest.mark.django_db(transaction=True)


async def start(project, bkpaas, version_id: str = "v2") -> PublicationTask:
    return await services.start_deployment(project, version_id, operator="alice", client_factory=lambda: bkpaas)


async def start_deploying(project, bkpaas, version_id: str = "v2") -> PublicationTask:
    """Start a deployment and submit it to the developer center, leaving it pending there."""
    task = await start(project, bkpaas, version_id)
    assert await steps.prepare_deployment(task.pk, bkpaas)
    await task.arefresh_from_db()
    return task


async def poll_deployment_once(task: PublicationTask, bkpaas) -> PublicationTask:
    await steps.poll_deployment(task.pk, bkpaas)
    await task.arefresh_from_db()
    return task


async def publish(project, bkpaas, version_id: str = "v1") -> PublicationTask:
    """Publish a version all the way to online."""
    task = await poll_deployment_once(await start_deploying(project, bkpaas, version_id), bkpaas)
    assert task.status == PublicationTaskStatus.SUCCESSFUL
    return task


async def interrupt(project) -> None:
    await services.interrupt_deployment(project, "bob")


async def unpublish(project) -> PublicationTask:
    task = await services.start_unpublish(project, "bob")
    await task.arefresh_from_db()
    return task


async def test_interrupt(project, bkpaas):
    """打包阶段当场结束；部署提交后只请求一次中断，并以开发者中心的结果为准。"""
    await publish(project, bkpaas, "v1")

    # 还没发出部署请求：不调用开发者中心，准备任务也不再提交部署。
    task = await start(project, bkpaas, "v2")
    await interrupt(project)
    assert bkpaas.called("interrupt_deployment") == []
    assert not await steps.prepare_deployment(task.pk, bkpaas)
    assert (await services.get_publication_state(project)).online.version_id == "v1"

    # 已提交：只发一次。中断生效后线上仍是 v1，不算失败。
    bkpaas.calls.clear()
    task = await start_deploying(project, bkpaas, "v2")
    await interrupt(project)
    with pytest.raises(PublicationInterruptConflictError, match=steps.MSG_INTERRUPT_REQUESTED):
        await interrupt(project)

    assert len(bkpaas.called("interrupt_deployment")) == 1
    bkpaas.queue("get_deployment_result", DeploymentResult("interrupted"))
    await poll_deployment_once(task, bkpaas)
    state = await services.get_publication_state(project)
    assert state.online.version_id == "v1"
    assert state.last_failure is None

    # 没人在 AppSpark 里请求过，是别人在开发者中心里中断的：记失败。
    task = await start_deploying(project, bkpaas, "v2")
    bkpaas.queue("get_deployment_result", DeploymentResult("interrupted"))
    task = await poll_deployment_once(task, bkpaas)
    assert task.error == steps.MSG_DEPLOY_INTERRUPTED

    # 部署请求已发出、ID 还没回来，没法告诉开发者中心中断哪一次。
    task = await start(project, bkpaas, "v2")
    await PublicationTask.objects.filter(pk=task.pk).aupdate(stage="deploying", deploy_requested_at=timezone.now())
    with pytest.raises(PublicationInterruptConflictError, match=steps.MSG_INTERRUPT_SUBMITTING):
        await interrupt(project)


async def test_unpublish(project, bkpaas, queued):
    """下架成功后没有线上版本，再发布复用原应用；开发者中心的两种拒绝要分开记。"""
    await publish(project, bkpaas, "v1")
    queued.clear()
    bkpaas.calls.clear()

    task = await unpublish(project)
    assert queued == [("unpublish_poll", task.pk)]
    assert await steps.poll_offline(task.pk, bkpaas)
    assert (await services.get_publication_state(project)).online is None

    # 绑定还在，再发布不创建应用。
    bkpaas.calls.clear()
    await publish(project, bkpaas, "v2")
    assert bkpaas.called("create_app") == []

    # 环境从没部署过，按已下架；已有下架在进行则记失败，线上不动。
    queued.clear()
    bkpaas.queue("offline", BkPaaSApiError(400, "x", code=OFFLINE_ENV_NOT_DEPLOYED_CODE))
    task = await unpublish(project)
    assert task.status == PublicationTaskStatus.SUCCESSFUL
    assert queued == []

    await publish(project, bkpaas, "v2")
    bkpaas.queue("offline", BkPaaSApiError(400, "x", code=OFFLINE_ALREADY_IN_PROGRESS_CODE))
    task = await unpublish(project)
    assert task.error == steps.MSG_UNPUBLISH_ALREADY_RUNNING
    assert (await services.get_publication_state(project)).online.version_id == "v2"
