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

"""第二步，在 Celery 准备任务里：打包、上传并提交部署。

打包和上传重做也安全，只有提交部署不能发两次，所以任务只做一次，靠 prepare_started_at 认领。
"""

import logging
from http import HTTPStatus

import httpx2
from django.utils import timezone

from app_spark_api.infras.bk_paas import BkPaaSApiError, BkPaaSClient, BkPaaSError
from app_spark_api.publication import packaging
from app_spark_api.publication.constants import PublicationStage, PublicationTaskStatus
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask
from app_spark_api.publication.packaging import SourcePackagingError
from app_spark_api.publication.steps.errors import (
    MSG_DEPLOY_UNCERTAIN,
    MSG_PREPARE_FAILED,
    MSG_PREPARE_INTERRUPTED,
    FailureCause,
    PublicationStepError,
    to_step_error,
)
from app_spark_api.publication.steps.progress import advance_stage, afinish_task

logger = logging.getLogger(__name__)


async def prepare_deployment(task_id: int, client: BkPaaSClient) -> bool:
    """打包、上传并提交部署；任一步失败就记下任务失败。

    :return: 是否提交了部署；为 True 时由调用方开始轮询。
    """
    # 先占住任务：重复投递、worker 崩溃后的重投都会撞上已写入的时间，直接丢掉。崩溃的那次不重做，
    # 由查询发布状态时的兜底判失败。
    claimed = await (
        PublicationTask.objects.pending()
        .filter(pk=task_id, prepare_started_at__isnull=True)
        .aupdate(prepare_started_at=timezone.now())
    )
    if not claimed:
        return False

    task = await PublicationTask.objects.select_related("project").aget(pk=task_id)
    try:
        await _submit_deployment(task, client)
    except PublicationStepError as exc:
        await afinish_task(task, PublicationTaskStatus.FAILED, error=exc.message)
        return False
    except Exception:
        # 数据库抖动这类意外也要收场，否则项目要等兜底超时才放开。发出过部署请求的，同样不确定是否生效。
        logger.exception("Preparing the deployment of publication task %s failed", task_id)
        error = MSG_DEPLOY_UNCERTAIN if task.deploy_requested_at else MSG_PREPARE_FAILED
        await afinish_task(task, PublicationTaskStatus.FAILED, error=error)
        return False

    return True


async def _submit_deployment(task: PublicationTask, client: BkPaaSClient) -> None:
    binding = await BkPaaSAppBinding.objects.aget(project_id=task.project_id)
    try:
        packaged = await packaging.apackage_version(task.project, task.version_id)

        await advance_stage(task, PublicationStage.UPLOADING)
        await client.upload_package_via_link(
            code=binding.app_code,
            module=binding.module_name,
            package_url=packaged.package_url,
            version=packaged.version,
            operator=task.operator,
            build_method=packaging.BUILD_METHOD,
        )
    except (BkPaaSError, httpx2.HTTPError, SourcePackagingError) as exc:
        raise to_step_error(exc) from exc

    # 按「仍在进行中」写入：打包太慢、已被兜底判失败的任务不能再去部署，否则失败的任务会在开发者中心上线。
    requested_at = timezone.now()
    marked = (
        await PublicationTask.objects.pending()
        .filter(pk=task.pk)
        .aupdate(stage=PublicationStage.DEPLOYING, deploy_requested_at=requested_at, updated_at=requested_at)
    )
    if not marked:
        raise PublicationStepError(MSG_PREPARE_INTERRUPTED, FailureCause.INTERNAL)

    task.deploy_requested_at = requested_at
    try:
        deployment = await client.deploy(
            code=binding.app_code, module=binding.module_name, version=packaged.version, operator=task.operator
        )
    except (BkPaaSError, httpx2.HTTPError) as exc:
        # 超时、5xx、读不懂的响应：请求可能已在开发者中心生效，再发只会多一次部署或被拒，交给用户去确认。
        # 其余 4xx 是开发者中心明确拒绝了，原因可以直接展示。
        if isinstance(exc, BkPaaSApiError) and exc.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
            raise to_step_error(exc) from exc

        raise PublicationStepError(MSG_DEPLOY_UNCERTAIN, FailureCause.UNAVAILABLE) from exc

    # 按「仍在进行中」写入：等响应期间任务可能已被兜底判失败。那样的任务不再轮询，但留下部署 ID，
    # 失败详情能直接指向这次部署。
    submitted_at = timezone.now()
    task.deployment_id = deployment.deployment_id
    recorded = (
        await PublicationTask.objects.pending()
        .filter(pk=task.pk)
        .aupdate(deployment_id=deployment.deployment_id, deploy_submitted_at=submitted_at, updated_at=submitted_at)
    )
    if not recorded:
        await PublicationTask.objects.filter(pk=task.pk).aupdate(deployment_id=deployment.deployment_id)
        logger.warning("Deployment %s was submitted after publication task %s had ended", task.deployment_id, task.pk)
        raise PublicationStepError(MSG_DEPLOY_UNCERTAIN, FailureCause.UNAVAILABLE)
