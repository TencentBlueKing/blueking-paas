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

"""发布的各个步骤。

1. 请求里调 bind_app 创建应用（已绑定则跳过），阶段推进到 packaging。
2. Celery 准备任务调 prepare_deployment，认领后由 _submit_deployment 打包、上传并提交部署。
3. 提交成功返回 True，调用方开始轮询 poll_deployment。
4. 部署结束后 _record_finished_deployment 经 afinish_task 写下结果。
5. 任一步的异常用 describe_error 整理成给用户看的原因。

创建应用很快，放在请求里，失败原因当场告诉用户。打包、上传、提交部署可能要几分钟，交给 Celery 准备任务；
打包和上传重做也安全，只有提交部署不能发两次。轮询只读，只有记录结果要保证只生效一次。
"""

import logging
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx2
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from app_spark_api.infras.bk_paas import (
    BkPaaSApiError,
    BkPaaSClient,
    BkPaaSConfigurationError,
    BkPaaSError,
    BkPaaSUnavailableError,
    CreatedApp,
    DeploymentResult,
    DeploymentStatus,
)
from app_spark_api.publication import packaging
from app_spark_api.publication.constants import (
    DEPLOY_POLL_INTERVAL_SECONDS,
    DEPLOY_TIMEOUT,
    MAX_POLLS_FOR_ACCESS_URL,
    PublicationStage,
    PublicationTaskStatus,
)
from app_spark_api.publication.models import DevCenterAppBinding, PublicationTask
from app_spark_api.publication.packaging import SourcePackagingError

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project

logger = logging.getLogger(__name__)

# 给用户看的失败原因。开发者中心返回的业务错误原样展示，下面这些是它没给出可读信息时的说法。
MSG_DEV_CENTER_UNAVAILABLE = "开发者中心暂时不可用"
MSG_APP_NOT_MANAGED = "该应用已在开发者中心改为其他部署方式，AppSpark 无法继续管理，请到开发者中心操作"
MSG_NOT_AUTHORIZED = "AppSpark 未获得开发者中心授权，请联系管理员"
MSG_NOT_CONFIGURED = "AppSpark 未完成开发者中心对接配置，请联系管理员"
MSG_DEPLOY_FAILED = "部署失败，请到开发者中心查看部署日志"
MSG_DEPLOY_INTERRUPTED = "部署已在开发者中心被中断"
MSG_DEPLOY_TIMEOUT = "部署超过 {minutes} 分钟仍未结束，请到开发者中心查看部署进度"
MSG_PREPARE_INTERRUPTED = "发布因服务重启中断，请重试"
MSG_PREPARE_FAILED = "发布时出现内部错误，请重试"
MSG_DEPLOY_UNCERTAIN = "部署请求可能已经提交，请到开发者中心查看部署记录"
MSG_MODULE_NOT_DEFAULT = "AppSpark 只能发布应用的默认模块，该应用的默认模块已在开发者中心变更，请到开发者中心操作"
MSG_APP_NOT_RECORDED = "开发者中心已创建应用 {code}，但 AppSpark 没能记下它，请联系管理员"
# 开发者中心 403 的错误码与给用户的说法。不在这里的 403（调用方没注册为 AppSpark 角色、网关没授权）要管理员处理。
_FORBIDDEN_MESSAGES = {
    "APP_SPARK_APP_REQUIRED": MSG_APP_NOT_MANAGED,
    "APP_SPARK_MODULE_REQUIRED": MSG_MODULE_NOT_DEFAULT,
}
# 两条轮询前后脚到达时只放一条过去；间隔取半个轮询周期，正常的下一轮不会被误拦。
_HALF_POLL_INTERVAL = timedelta(seconds=DEPLOY_POLL_INTERVAL_SECONDS / 2)


class PublicationStepError(Exception):
    """某一步失败，message 就是给用户看的原因。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


async def bind_app(
    task: PublicationTask, project: Project, client: BkPaaSClient, *, app_code: str, app_name: str
) -> None:
    """首次发布时创建开发者中心应用，然后把任务推进到打包。

    :raises PublicationStepError: 创建应用失败，消息就是给用户看的原因。
    """
    if not await DevCenterAppBinding.objects.filter(project=project).aexists():
        try:
            app = await client.create_app(
                code=app_code, name=app_name, operator=task.operator, **_build_tenant_kwargs(project)
            )
        except (BkPaaSError, httpx2.HTTPError) as exc:
            raise PublicationStepError(describe_error(exc)) from exc

        # 应用已经建好，记不下来时下次发布会被「应用 ID 已存在」挡住，要让用户知道找管理员处理。
        try:
            await sync_to_async(_record_app)(project, app)
        except Exception as exc:
            logger.exception("Recording developer center app %s of project %s failed", app.code, project.pk)
            raise PublicationStepError(MSG_APP_NOT_RECORDED.format(code=app.code)) from exc

    await _advance_stage(task, PublicationStage.PACKAGING)


def _record_app(project: Project, app: CreatedApp) -> None:
    # 应用已经在开发者中心建好，没有绑定的话这个项目再也发布不了。
    DevCenterAppBinding.objects.create(
        project=project, app_code=app.code, module_name=app.default_module, tenant_id=project.tenant_id
    )


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
    binding = await DevCenterAppBinding.objects.aget(project_id=task.project_id)
    try:
        packaged = await packaging.apackage_version(task.project, task.version_id)

        await _advance_stage(task, PublicationStage.UPLOADING)
        await client.upload_package_via_link(
            code=binding.app_code,
            module=binding.module_name,
            package_url=packaged.package_url,
            version=packaged.version,
            operator=task.operator,
            build_method=packaging.BUILD_METHOD,
        )
    except (BkPaaSError, httpx2.HTTPError, SourcePackagingError) as exc:
        raise PublicationStepError(describe_error(exc)) from exc

    # 按「仍在进行中」写入：打包太慢、已被兜底判失败的任务不能再去部署，否则失败的任务会在开发者中心上线。
    requested_at = timezone.now()
    marked = (
        await PublicationTask.objects.pending()
        .filter(pk=task.pk)
        .aupdate(stage=PublicationStage.DEPLOYING, deploy_requested_at=requested_at, updated_at=requested_at)
    )
    if not marked:
        raise PublicationStepError(MSG_PREPARE_INTERRUPTED)

    task.deploy_requested_at = requested_at
    try:
        deployment = await client.deploy(
            code=binding.app_code, module=binding.module_name, version=packaged.version, operator=task.operator
        )
    except (BkPaaSError, httpx2.HTTPError) as exc:
        # 超时、5xx、读不懂的响应：请求可能已在开发者中心生效，再发只会多一次部署或被拒，交给用户去确认。
        # 其余 4xx 是开发者中心明确拒绝了，原因可以直接展示。
        if isinstance(exc, BkPaaSApiError) and exc.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
            raise PublicationStepError(describe_error(exc)) from exc

        raise PublicationStepError(MSG_DEPLOY_UNCERTAIN) from exc

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
        raise PublicationStepError(MSG_DEPLOY_UNCERTAIN)


async def poll_deployment(task_id: int, client: BkPaaSClient) -> float | None:
    """查看一次已提交的部署，结束了就记下任务结果。

    :return: 多少秒后再查；任务已结束、或另一条轮询刚查过时为 None。
    """
    now = timezone.now()

    # 先占住这一轮：重复投递、兜底重投的消息会在同一时间段里撞上，只让其中一条去查，其余直接丢掉。
    claimed = await (
        PublicationTask.objects.pending()
        .filter(pk=task_id)
        .filter(Q(last_polled_at__isnull=True) | Q(last_polled_at__lte=now - _HALF_POLL_INTERVAL))
        .aupdate(last_polled_at=now)
    )
    if not claimed:
        return None

    task = await PublicationTask.objects.aget(pk=task_id)
    binding = await DevCenterAppBinding.objects.aget(project_id=task.project_id)
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
            await afinish_task(task, PublicationTaskStatus.FAILED, error=describe_error(exc))
            return None

        logger.warning("Polling deployment %s failed, will retry: %s", task.deployment_id, exc)
        result = None

    if result is not None and result.is_finished:
        return await _record_finished_deployment(task, result)

    # 还没结束（或这次没问到）：超时就判失败，否则过一会儿再看。
    if timezone.now() >= (task.deploy_submitted_at or now) + DEPLOY_TIMEOUT:
        minutes = int(DEPLOY_TIMEOUT.total_seconds() // 60)
        await afinish_task(task, PublicationTaskStatus.FAILED, error=MSG_DEPLOY_TIMEOUT.format(minutes=minutes))
        return None

    return DEPLOY_POLL_INTERVAL_SECONDS


async def afinish_task(
    task: PublicationTask,
    status: PublicationTaskStatus,
    *,
    error: str = "",
    access_url: str = "",
    notify: bool = True,
    before_deploy_request: bool = False,
    before_deployment_submitted: bool = False,
) -> bool:
    """给仍在进行中的任务写下结果。

    :param notify: 是否作为「还没看过的结果」提醒用户。发布请求里创建应用失败时用户当场就看到了，不用再提醒。
    :param before_deploy_request: 只在还没发出部署请求时结束。兜底按读到的旧状态判失败时用它，免得把
        刚发出部署请求、正在等响应的任务判掉。
    :param before_deployment_submitted: 只在还没记下部署 ID 时结束，理由同上，免得判掉刚拿到部署 ID 的任务。
    :return: 是否由这次调用结束了任务；任务早已结束（如另一条轮询抢先记了结果）时为 False。
    """
    now = timezone.now()
    # 按「仍在进行中」更新：并发的两条轮询只有一条能记结果，后到的什么都不改。
    query = PublicationTask.objects.pending().filter(pk=task.pk)
    if before_deploy_request:
        query = query.filter(deploy_requested_at__isnull=True)

    if before_deployment_submitted:
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


async def _record_finished_deployment(task: PublicationTask, result: DeploymentResult) -> float | None:
    if result.status == DeploymentStatus.SUCCESSFUL:
        # 成功但还没有访问地址时多查几轮：地址是要分享给同事的，首次发布不能记成空的。
        if not result.access_url and task.access_url_polls < MAX_POLLS_FOR_ACCESS_URL:
            await PublicationTask.objects.filter(pk=task.pk).aupdate(access_url_polls=task.access_url_polls + 1)
            return DEPLOY_POLL_INTERVAL_SECONDS

        await afinish_task(task, PublicationTaskStatus.SUCCESSFUL, access_url=result.access_url or "")
        return None

    error = MSG_DEPLOY_INTERRUPTED if result.status == DeploymentStatus.INTERRUPTED else result.error_detail
    await afinish_task(task, PublicationTaskStatus.FAILED, error=error or MSG_DEPLOY_FAILED)
    return None


async def _advance_stage(task: PublicationTask, stage: PublicationStage) -> None:
    # 前端轮询发布状态，按 stage 展示进度。按「仍在进行中」写入：打包太慢、已被兜底判失败的任务，
    # 到这里就停下，不再去上传。
    advanced = (
        await PublicationTask.objects.pending().filter(pk=task.pk).aupdate(stage=stage, updated_at=timezone.now())
    )
    if not advanced:
        raise PublicationStepError(MSG_PREPARE_INTERRUPTED)

    task.stage = stage


def describe_error(exc: BkPaaSError | httpx2.HTTPError | SourcePackagingError) -> str:
    """把失败整理成给用户看的原因；网络错误说成开发者中心暂时不可用。"""
    if isinstance(exc, SourcePackagingError):
        return str(exc)

    if isinstance(exc, BkPaaSConfigurationError):
        return MSG_NOT_CONFIGURED

    if isinstance(exc, BkPaaSApiError):
        # 几种 403 要分开说，只能靠错误码区分：有的要用户去开发者中心处理，有的要管理员处理。
        if exc.status_code == HTTPStatus.FORBIDDEN:
            return _FORBIDDEN_MESSAGES.get(exc.code or "", MSG_NOT_AUTHORIZED)

        # 5xx 的说明多半是英文的服务端报错，对用户没用，统一说暂时不可用。
        if exc.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
            return exc.message

    return MSG_DEV_CENTER_UNAVAILABLE


def _build_tenant_kwargs(project: Project) -> dict[str, str]:
    # 非多租户时开发者中心自己固定租户信息，传了也会被忽略，所以不传。
    if not settings.ENABLE_MULTI_TENANT_MODE:
        return {}

    return {"app_tenant_mode": "single", "app_tenant_id": project.tenant_id}
