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

"""发布状态的查询，发布、中断、下架的发起：接口层调这里。

发起发布时在请求里同步创建应用，失败直接告诉用户；打包、上传、提交部署和之后的轮询都在 Celery 上（见 tasks）。
下架在请求里同步发起，之后的轮询同样在 Celery 上。中断作用在进行中的发布任务上，不新建任务。
发布状态全部从任务表推出来：最近一次成功的任务是发布时，它的版本就是线上版本，是下架时没有线上版本；
最近一次失败是最近结束（不算已中断的）、且失败了的那个任务。
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import attrs
import httpx2
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.infras.bk_paas import (
    BkPaaSClient,
    BkPaaSConfigurationError,
    BkPaaSError,
    ConsoleLinks,
    build_console_links,
    build_deployment_detail_url,
)
from app_spark_api.publication import packaging, steps, tasks
from app_spark_api.publication.app_name import ensure_app_creatable, normalize_app_name, resolve_default_app_name
from app_spark_api.publication.constants import (
    DEPLOY_REQUEST_TIMEOUT,
    DEPLOY_TIMEOUT,
    PREPARE_TIMEOUT,
    PublicationStage,
    PublicationTaskKind,
    PublicationTaskStatus,
)
from app_spark_api.publication.exceptions import (
    PublicationAppNameConflictError,
    PublicationAppNameInvalidError,
    PublicationInterruptConflictError,
    PublicationNotInterruptibleError,
    PublicationNotOnlineError,
    PublicationNoVersionError,
    PublicationProjectGoneError,
    PublicationSubmitError,
    PublicationTaskInProgressError,
    PublicationVersionNotFoundError,
)
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from datetime import datetime

logger = logging.getLogger(__name__)


@attrs.frozen
class OnlineVersion:
    """The version serving in the developer center."""

    version_id: str
    url: str
    published_at: datetime | None


@attrs.frozen
class PublicationFailure:
    """The latest task, which failed.

    :param detail_url: 开发者中心里的详情页：提交过部署时是那次部署的日志，否则是部署管理页。
    """

    kind: str
    version_id: str
    is_update: bool
    error: str
    failed_at: datetime | None
    detail_url: str | None


@attrs.frozen
class UnseenResult:
    """The result of the latest task, which the publish panel opens by itself until the owner has looked at it."""

    kind: str
    status: str


@attrs.frozen
class PublicationState:
    """Everything the publish panel shows about one Project.

    :param online: 线上版本，未发布时为 None。
    :param task: 进行中的任务，没有时为 None。
    :param last_failure: 最近结束的任务失败了时为它，否则为 None。
    :param unseen_result: 发布面板打开时要主动展开的最近一次任务结果；用户点开看过、或有任务在进行时为 None。
    :param app_code: 已绑定的开发者中心应用 ID，首次发布创建应用前为 None。
    :param default_app_name: 首次发布时弹窗里预填的应用名称；已绑定应用后为 None。
    :param console_links: 开发者中心页面链接，未绑定应用或没配置站点地址时为 None。
    :param latest_version_id: 不指定版本时会发布的最新版本，项目还没有版本时为 None。
    """

    online: OnlineVersion | None
    task: PublicationTask | None
    last_failure: PublicationFailure | None
    unseen_result: UnseenResult | None
    app_code: str | None
    default_app_name: str | None
    console_links: ConsoleLinks | None
    latest_version_id: str | None


async def start_deployment(
    project: Project,
    version_id: str | None,
    operator: str,
    *,
    app_name: str | None = None,
    client_factory: Callable[[], BkPaaSClient] | None = None,
) -> PublicationTask:
    """Start deploying a version to the developer center: create the application if needed, and queue the rest.

    :param version_id: 要发布的版本，None 表示发最新版本。
    :param operator: 发起人用户名，作为开发者中心应用管理员和各操作的记录人。
    :param app_name: 首次发布时创建的应用名称，默认见 resolve_default_app_name；已绑定应用时忽略。
    :param client_factory: 构造开发者中心客户端，默认按配置构造。
    :raises PublicationNoVersionError: 没指定版本，项目也还没有任何版本。
    :raises PublicationVersionNotFoundError: 版本不属于该项目。
    :raises PublicationAppNameInvalidError: 首次发布时应用名称按开发者中心的规则过滤后为空。
    :raises PublicationAppNameConflictError: 首次发布时应用名称已被开发者中心的其他应用使用。
    :raises PublicationTaskInProgressError: 项目已有发布任务在进行。
    :raises PublicationProjectGoneError: 项目刚被删除。
    :raises PublicationSubmitError: 开发者中心提前拒绝了应用 ID 或名称（不建任务），或创建应用失败（任务已记为失败）。
    """
    # 发布暂不支持选版本，前端不传版本时发最新的；任务里记下实际发的版本，线上版本和失败记录据此展示。
    if version_id is None:
        version_id = await packaging.alatest_version(project)
        if version_id is None:
            raise PublicationNoVersionError(f"Project {project.pk} has no version to publish")

    elif not await packaging.aversion_exists(project, version_id):
        raise PublicationVersionNotFoundError(f"Project {project.pk} has no publishable version {version_id!r}")

    factory = client_factory or BkPaaSClient.from_settings

    # 已绑定的项目复用原应用，不需要名称。名称只在开发者中心里要求租户内唯一，本地不存，
    # 建任务前先问开发者中心，重名时让用户改名，不留下一次失败的发布。
    name = ""
    if not await BkPaaSAppBinding.objects.filter(project=project).aexists():
        name = normalize_app_name(app_name) if app_name is not None else resolve_default_app_name(project)
        if not name:
            raise PublicationAppNameInvalidError(app_name or "")

        await ensure_app_creatable(project, factory, name)

    task = await sync_to_async(_create_deployment_task)(project, version_id, operator)

    # 浏览器断开时 Django 会取消正在处理的请求。创建应用一旦开始就要做完，否则开发者中心里建好了应用，
    # 这边却没记下绑定。应用 ID 就是项目 ID，规则由开发者中心校验。
    await _complete_even_if_cancelled(_bind_and_queue(task, project, factory, project.id, name))
    return task


async def afail_pending_tasks(project: Project, error: str) -> None:
    """Fail the Project's pending publication tasks, e.g. before the Project is deleted."""
    async for task in PublicationTask.objects.pending().filter(project=project):
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=error)


def _lock_for_new_task(project: Project) -> None:
    """Lock the Project row and make sure it has no running task; call inside a transaction."""
    # 锁住项目行再看有没有进行中的任务：两个并发的发起只有一个能建出任务，另一个返回 409。
    # 查任务也用加锁读：MySQL 默认的 REPEATABLE READ 下，普通读可能看不到对方刚提交的任务。
    # 项目刚被删除时锁不到行：不能再为它建任务、建应用。
    if Project.objects.select_for_update().filter(pk=project.pk).first() is None:
        raise PublicationProjectGoneError(f"Project {project.pk} is gone")

    if PublicationTask.objects.select_for_update().pending().filter(project=project).first() is not None:
        raise PublicationTaskInProgressError(f"Project {project.pk} already has a running publication task")


def _create_deployment_task(project: Project, version_id: str, operator: str) -> PublicationTask:
    with transaction.atomic():
        _lock_for_new_task(project)
        return PublicationTask.objects.create(
            project=project,
            kind=PublicationTaskKind.DEPLOYMENT,
            version_id=version_id,
            # 发起时就定下来：失败记录要据此说「更新版本失败」还是「发布失败」。下架之后再发布算首次发布。
            is_update=_find_online_task(project) is not None,
            operator=operator,
            stage=PublicationStage.BINDING,
            tenant_id=project.tenant_id,
        )


def _find_online_task(project: Project) -> PublicationTask | None:
    """Return the deployment serving now, or None when the Project was never published or has been unpublished."""
    latest = PublicationTask.objects.filter(project=project).succeeded().first()
    if latest is None or latest.kind != PublicationTaskKind.DEPLOYMENT:
        return None

    return latest


async def _bind_and_queue(
    task: PublicationTask, project: Project, client_factory: Callable[[], BkPaaSClient], app_code: str, app_name: str
) -> None:
    try:
        async with client_factory() as client:
            await steps.bind_app(task, project, client, app_code=app_code, app_name=app_name)
    except steps.AppNameTakenError as exc:
        # 发起前校验时名称还空着，创建时被别人抢先用了：任务照样当场结束，但按重名回答，让用户改名。
        await _fail_submission(task, exc)
        raise PublicationAppNameConflictError(app_name) from exc
    except steps.PublicationStepError as exc:
        raise await _fail_submission(task, exc) from exc
    except BkPaaSConfigurationError as exc:
        # 构造客户端时就发现没配好对接，和步骤里的失败一样当场告诉用户。
        raise await _fail_submission(task, steps.to_step_error(exc)) from exc
    except Exception as exc:
        # 数据库抖动这类意外也要当场收场，否则任务挂在进行中，项目要等兜底超时才放开。
        logger.exception("Binding the developer center app of publication task %s failed", task.pk)
        error = steps.PublicationStepError(steps.MSG_PREPARE_FAILED, steps.FailureCause.INTERNAL)
        raise await _fail_submission(task, error) from exc

    await _queue_preparation(task)


async def _fail_submission(task: PublicationTask, error: steps.PublicationStepError) -> PublicationSubmitError:
    """Fail the task on the spot and return the error to answer the request with."""
    # 用户在发布请求的响应里就会看到原因，不用再提醒一次。
    await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=error.message, notify=False)
    return PublicationSubmitError(error.message, error.cause)


async def interrupt_deployment(project: Project, operator: str) -> None:
    """Interrupt the Project's running deployment, or refuse when there is nothing to interrupt."""
    task = await _get_running_deployment(project)

    # 创建应用在发布请求里同步进行，一两秒就过去；这时结束任务会提前放开项目，和接着的重新发布抢着建应用。
    if task.stage == PublicationStage.BINDING:
        raise PublicationInterruptConflictError(steps.MSG_INTERRUPT_BINDING)

    # 还没发出部署请求：开发者中心里什么都没发生，直接结束，准备任务推进下一步时会发现任务已结束而停下。
    # 守卫挡的是这一刻准备任务刚发出部署请求的情况，那时要按已提交的部署处理，所以守卫没过就重新读一次再判。
    if task.deploy_requested_at is None:
        if await steps.afinish_task(
            task, PublicationTaskStatus.INTERRUPTED, notify=False, guard=steps.FinishGuard.BEFORE_DEPLOY_REQUEST
        ):
            return

        task = await _get_running_deployment(project)

    # 同一任务只向开发者中心发一次中断，结果出来之前再点只提示稍候。
    if task.interrupt_requested_at is not None:
        raise PublicationInterruptConflictError(steps.MSG_INTERRUPT_REQUESTED)

    # 已发出部署请求、还没拿到部署 ID：没法告诉开发者中心中断哪一次，过几秒拿到 ID 再来。
    if not task.deployment_id:
        raise PublicationInterruptConflictError(steps.MSG_INTERRUPT_SUBMITTING)

    # 先查好绑定再写中断标记，免得查询出错时标记留下、用户在部署结束前都没法再中断。
    binding = await BkPaaSAppBinding.objects.aget(project_id=task.project_id)

    # 按「仍在进行中、还没人请求过中断」写入，并发的两次中断只有一次去调开发者中心。
    requested_at = timezone.now()
    claimed = (
        await PublicationTask.objects.pending()
        .filter(pk=task.pk, interrupt_requested_at__isnull=True)
        .aupdate(interrupt_requested_at=requested_at, interrupt_sent=True, updated_at=requested_at)
    )
    if not claimed:
        # 没写成也可能是任务这一刻刚结束，那就没什么可中断的了。
        await _get_running_deployment(project)
        raise PublicationInterruptConflictError(steps.MSG_INTERRUPT_REQUESTED)

    # 浏览器断开时也要做完：调用失败要把中断标记清掉，否则用户在部署结束前都没法再中断。
    await _complete_even_if_cancelled(_request_interruption(task, binding, operator, requested_at))


async def _get_running_deployment(project: Project) -> PublicationTask:
    task = await PublicationTask.objects.pending().filter(project=project).afirst()
    if task is None or task.kind != PublicationTaskKind.DEPLOYMENT:
        raise PublicationNotInterruptibleError(f"Project {project.pk} has no running deployment")

    return task


async def _request_interruption(
    task: PublicationTask, binding: BkPaaSAppBinding, operator: str, requested_at: datetime
) -> None:
    try:
        async with BkPaaSClient.from_settings() as client:
            await client.interrupt_deployment(
                code=binding.app_code, module=binding.module_name, deployment_id=task.deployment_id, operator=operator
            )
    except (BkPaaSError, httpx2.HTTPError) as exc:
        # 清掉标记让用户可以再试；只清自己写下的那次，不碰后来的。interrupt_sent 留着，见模型上的说明。
        await (
            PublicationTask.objects.pending()
            .filter(pk=task.pk, interrupt_requested_at=requested_at)
            .aupdate(interrupt_requested_at=None)
        )

        # 开发者中心按规则拒绝的（预备执行中、已结束、应用已脱离管理）任务都还在继续，原样说明，让用户稍后再试；
        # 不可用、没配好对接沿用发布的错误分类。
        error = steps.to_step_error(exc)
        if error.cause == steps.FailureCause.REJECTED:
            raise PublicationInterruptConflictError(error.message) from exc

        raise error from exc


async def start_unpublish(project: Project, operator: str) -> PublicationTask:
    """Take the Project offline in the developer center and queue polling the result."""
    task = await sync_to_async(_create_unpublish_task)(project, operator)

    # 浏览器断开时也要做完：下架一旦发出，就要记下下架操作 ID 并开始轮询，否则只能等兜底超时。
    await _complete_even_if_cancelled(_submit_and_poll_offline(task))
    return task


def _create_unpublish_task(project: Project, operator: str) -> PublicationTask:
    with transaction.atomic():
        _lock_for_new_task(project)

        # 在锁里判断：并发的另一次下架可能刚刚成功。
        online = _find_online_task(project)
        if online is None:
            raise PublicationNotOnlineError(f"Project {project.pk} is not online")

        return PublicationTask.objects.create(
            project=project,
            kind=PublicationTaskKind.UNPUBLISH,
            version_id=online.version_id,
            is_update=True,
            operator=operator,
            stage=PublicationStage.UNPUBLISHING,
            tenant_id=project.tenant_id,
        )


async def _submit_and_poll_offline(task: PublicationTask) -> None:
    try:
        client = BkPaaSClient.from_settings()
    except BkPaaSConfigurationError as exc:
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.to_step_error(exc).message)
        return

    async with client:
        submitted = await steps.submit_offline(task, client)

    if not submitted:
        return

    # 下架已经发出，投递失败也不能撤回；轮询没起来时，查询发布状态的兜底会在下架超时后判失败。
    try:
        await asyncio.to_thread(tasks.schedule_unpublish_poll, task.pk)
    except Exception:
        logger.exception("Queueing the poll of unpublish task %s failed", task.pk)


async def _queue_preparation(task: PublicationTask) -> None:
    """Queue the Celery task that packs, uploads and submits the deployment."""
    # apply_async 是同步的，会堵住事件循环，放到线程里投。
    try:
        await asyncio.to_thread(tasks.schedule_deployment_prepare, task.pk)
    except Exception:
        # 投递失败不撤回任务：准备任务没开始的，查询发布状态时兜底超时判失败，用户重试即可。
        logger.exception("Queueing the preparation of publication task %s failed", task.pk)


async def _handle_stalled_task(task: PublicationTask) -> None:
    """Fail a task that will not end by itself."""
    now = timezone.now()

    if task.kind == PublicationTaskKind.UNPUBLISH:
        await _handle_stalled_unpublish(task, now)
        return

    # 部署超时一般由轮询判。轮询停掉了（投递失败、worker 崩溃丢了消息）就没人再判，这里兜住，
    # 免得项目一直卡在进行中。
    if task.deployment_id:
        if (task.deploy_submitted_at or task.started_at) <= now - DEPLOY_TIMEOUT:
            await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.make_deploy_timeout_message())
        return

    # 发出了部署请求却一直没记下部署 ID：发请求的 worker 中途没了，部署是否生效说不准，不能再发一次。
    # 从发出请求算起，等过一次请求超时再判，免得判掉还在等响应的部署。
    if task.deploy_requested_at:
        # 读到的状态可能已经过时（worker 刚记下部署 ID），所以只在仍没有部署 ID 时判失败。
        if task.deploy_requested_at <= now - DEPLOY_REQUEST_TIMEOUT:
            await steps.afinish_task(
                task,
                PublicationTaskStatus.FAILED,
                error=steps.MSG_DEPLOY_UNCERTAIN,
                guard=steps.FinishGuard.BEFORE_DEPLOYMENT_SUBMITTED,
            )
        return

    # 很久还没发出部署请求：进程中途没了或队列一直不可用。读到的状态可能已经过时（worker 刚发出部署请求），
    # 所以只在仍未发出请求时判失败。
    if task.started_at <= now - PREPARE_TIMEOUT:
        await steps.afinish_task(
            task,
            PublicationTaskStatus.FAILED,
            error=steps.MSG_PREPARE_INTERRUPTED,
            guard=steps.FinishGuard.BEFORE_DEPLOY_REQUEST,
        )


async def _handle_stalled_unpublish(task: PublicationTask, now: datetime) -> None:
    # 下架超时一般由轮询判。轮询停掉了（投递失败、worker 崩溃丢了消息）就没人再判，这里兜住。
    if task.offline_operation_id:
        if task.started_at <= now - DEPLOY_TIMEOUT:
            await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.make_unpublish_timeout_message())
        return

    # 发起下架的请求中途没了（如 Pod 重启），没记下下架操作 ID。下架可以重复发起，判失败让用户再点一次即可。
    # 等过一次请求超时再判，免得判掉还在等开发者中心响应的请求；读到的状态可能已经过时，所以只在仍没有 ID 时判。
    if task.started_at <= now - DEPLOY_REQUEST_TIMEOUT:
        await steps.afinish_task(
            task,
            PublicationTaskStatus.FAILED,
            error=steps.MSG_UNPUBLISH_INTERRUPTED,
            guard=steps.FinishGuard.BEFORE_OFFLINE_SUBMITTED,
        )


async def get_publication_state(project: Project) -> PublicationState:
    """Return where the Project stands in the developer center."""
    # 前端在任务进行中会反复来查，顺带给停住的任务一个兜底；兜底可能结束任务，所以之后再读一次。
    active = await PublicationTask.objects.pending().filter(project=project).afirst()
    if active is not None:
        await _handle_stalled_task(active)
        active = await PublicationTask.objects.pending().filter(project=project).afirst()

    binding = await BkPaaSAppBinding.objects.filter(project=project).afirst()
    links = None
    if binding is not None:
        links = build_console_links(settings.BKPAAS_URL, binding.app_code, binding.module_name)

    finished = PublicationTask.objects.filter(project=project).finished()

    # 已中断的任务不是失败，最近一次失败取它之前的那个任务。
    latest_concluded = await finished.exclude_interrupted().afirst()
    last_failure = None
    if latest_concluded is not None and latest_concluded.status == PublicationTaskStatus.FAILED:
        last_failure = _build_failure(latest_concluded, binding, links)

    # 新任务开始后，上一次的结果属于上一次任务，再展示只会和进行中的状态打架。要展开的结果不跳过已中断的任务：
    # 它结束时已记为看过，不会被展开；跳过它反而会把更早、还没看过的结果重新翻出来。
    latest = await finished.afirst()
    unseen_result = None
    if active is None and latest is not None and not latest.result_seen:
        unseen_result = UnseenResult(kind=latest.kind, status=latest.status)

    return PublicationState(
        online=await _get_online_version(project),
        task=active,
        last_failure=last_failure,
        unseen_result=unseen_result,
        app_code=None if binding is None else binding.app_code,
        default_app_name=resolve_default_app_name(project) if binding is None else None,
        console_links=links,
        latest_version_id=await packaging.alatest_version(project),
    )


async def _get_online_version(project: Project) -> OnlineVersion | None:
    latest = await sync_to_async(_find_online_task)(project)
    if latest is None:
        return None

    # 开发者中心偶尔拿不到访问地址：更新版本、下架后重新发布都不会改变访问地址，沿用之前记下的。
    url = latest.access_url
    if not url:
        successful = PublicationTask.objects.filter(project=project).successful_deployments()
        url = await successful.exclude(access_url="").values_list("access_url", flat=True).afirst() or ""

    return OnlineVersion(version_id=latest.version_id, url=url, published_at=latest.finished_at)


def _build_failure(
    task: PublicationTask, binding: BkPaaSAppBinding | None, links: ConsoleLinks | None
) -> PublicationFailure:
    detail_url = None if links is None else links.deployments
    if binding is not None and task.deployment_id:
        detail_url = build_deployment_detail_url(settings.BKPAAS_URL, binding.app_code, task.deployment_id)

    return PublicationFailure(
        kind=task.kind,
        version_id=task.version_id,
        is_update=task.is_update,
        error=task.error,
        failed_at=task.finished_at,
        detail_url=detail_url,
    )


async def clear_unseen_result(project: Project) -> None:
    """Stop opening the latest result by itself once the owner has looked at it."""
    await PublicationTask.objects.filter(project=project, result_seen=False).finished().aupdate(result_seen=True)


async def _complete_even_if_cancelled[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run coro to its end even if the caller is cancelled meanwhile, then let the cancellation through."""
    inner = asyncio.ensure_future(coro)
    try:
        return await asyncio.shield(inner)
    except asyncio.CancelledError:
        await asyncio.wait({inner})
        # 取出结果，避免它的异常在日志里报成「从没被取回」；调用方要的是取消，照常抛出取消。
        if not inner.cancelled():
            inner.exception()
        raise
