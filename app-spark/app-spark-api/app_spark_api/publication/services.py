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

"""发布状态的查询与发起：接口层调这里。

发起发布时在请求里同步创建应用，失败直接告诉用户；打包、上传、提交部署和之后的轮询都在 Celery 上（见 tasks）。
发布状态全部从任务表推出来：线上版本是最近一次成功的发布，最近一次失败是最近结束、且失败了的那个任务。
"""

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

import attrs
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.infras.bk_paas import (
    BkPaaSClient,
    BkPaaSConfigurationError,
    ConsoleLinks,
    build_console_links,
    build_deployment_detail_url,
)
from app_spark_api.publication import packaging, steps, tasks
from app_spark_api.publication.constants import (
    APP_NAME_MAX_LENGTH,
    DEPLOY_POLL_INTERVAL_SECONDS,
    DEPLOY_REQUEST_TIMEOUT,
    DEPLOY_TIMEOUT,
    POLL_STALL_AFTER,
    PREPARE_TIMEOUT,
    PublicationStage,
    PublicationTaskKind,
    PublicationTaskStatus,
)
from app_spark_api.publication.exceptions import (
    PublicationAppNameInvalidError,
    PublicationNoVersionError,
    PublicationSubmitError,
    PublicationTaskInProgressError,
    PublicationVersionNotFoundError,
)
from app_spark_api.publication.models import DevCenterAppBinding, PublicationTask

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from datetime import datetime

logger = logging.getLogger(__name__)

# 开发者中心的应用名称（NickNameField）去掉首尾空白后只保留这些字符，其余静默丢掉。
_APP_NAME_CHAR = re.compile(r"[\u4e00-\u9fa5\w\-_]")


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
    """The result of the latest task, until the owner has seen it."""

    kind: str
    status: str


@attrs.frozen
class PublicationState:
    """Everything the publish panel shows about one Project.

    :param online: 线上版本，未发布时为 None。
    :param task: 进行中的任务，没有时为 None。
    :param last_failure: 最近结束的任务失败了时为它，否则为 None。
    :param unseen_result: 用户还没看过的最近一次任务结果，没有时为 None。
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
    :raises PublicationTaskInProgressError: 项目已有发布任务在进行。
    :raises PublicationSubmitError: 创建应用失败，任务已记为失败。
    """
    # 发布暂不支持选版本，前端不传版本时发最新的；任务里记下实际发的版本，线上版本和失败记录据此展示。
    if version_id is None:
        version_id = await packaging.alatest_version(project)
        if version_id is None:
            raise PublicationNoVersionError(f"Project {project.pk} has no version to publish")

    elif not await packaging.aversion_exists(project, version_id):
        raise PublicationVersionNotFoundError(f"Project {project.pk} has no publishable version {version_id!r}")

    # 已绑定的项目复用原应用，不需要名称。名称只在开发者中心里要求租户内唯一，本地不存也不查重，
    # 重名由创建应用的报错说明。
    name = ""
    if not await DevCenterAppBinding.objects.filter(project=project).aexists():
        name = normalize_app_name(app_name) if app_name is not None else resolve_default_app_name(project)
        if not name:
            raise PublicationAppNameInvalidError(app_name or "")

    task = await sync_to_async(_create_deployment_task)(project, version_id, operator)

    # 浏览器断开时 Django 会取消正在处理的请求。创建应用一旦开始就要做完，否则开发者中心里建好了应用，
    # 这边却没记下绑定。应用 ID 就是项目 ID，规则由开发者中心校验。
    factory = client_factory or BkPaaSClient.from_settings
    await _complete_even_if_cancelled(_bind_and_queue(task, project, factory, project.id, name))
    return task


def resolve_default_app_name(project: Project) -> str:
    """Return the application name to suggest on the first deployment."""
    # 项目名称一般比 ID 好读；全是开发者中心不认的字符时退回 ID。
    return normalize_app_name(project.name) or project.id


def normalize_app_name(name: str) -> str:
    """Return the name the developer center would keep, cut to its length limit."""
    return "".join(_APP_NAME_CHAR.findall(name.strip()))[:APP_NAME_MAX_LENGTH]


async def afail_pending_tasks(project: Project, error: str) -> None:
    """Fail the Project's pending publication tasks, e.g. before the Project is deleted."""
    async for task in PublicationTask.objects.pending().filter(project=project):
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=error)


def _create_deployment_task(project: Project, version_id: str, operator: str) -> PublicationTask:
    with transaction.atomic():
        # 锁住项目行再看有没有进行中的任务：两个并发的发起只有一个能建出任务，另一个返回 409。
        # 查任务也用加锁读：MySQL 默认的 REPEATABLE READ 下，普通读可能看不到对方刚提交的任务。
        # 项目刚被删除时锁不到行：不能再为它建任务、建应用。
        if Project.objects.select_for_update().filter(pk=project.pk).first() is None:
            raise Http404(f"Project {project.pk} is gone")

        if PublicationTask.objects.select_for_update().pending().filter(project=project).first() is not None:
            raise PublicationTaskInProgressError(f"Project {project.pk} already has a running publication task")

        return PublicationTask.objects.create(
            project=project,
            kind=PublicationTaskKind.DEPLOYMENT,
            version_id=version_id,
            # 发起时就定下来：失败记录要据此说「更新版本失败」还是「发布失败」。
            is_update=PublicationTask.objects.online().filter(project=project).exists(),
            operator=operator,
            stage=PublicationStage.BINDING,
            tenant_id=project.tenant_id,
        )


async def _bind_and_queue(
    task: PublicationTask, project: Project, client_factory: Callable[[], BkPaaSClient], app_code: str, app_name: str
) -> None:
    try:
        async with client_factory() as client:
            await steps.bind_app(task, project, client, app_code=app_code, app_name=app_name)
    except (steps.PublicationStepError, BkPaaSConfigurationError) as exc:
        message = exc.message if isinstance(exc, steps.PublicationStepError) else steps.describe_error(exc)
        # 用户在发布请求的响应里就会看到原因，不用再提醒一次。
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=message, notify=False)
        raise PublicationSubmitError(message) from exc
    except Exception as exc:
        # 数据库抖动这类意外也要当场收场，否则任务挂在进行中，项目要等兜底超时才放开。
        logger.exception("Binding the developer center app of publication task %s failed", task.pk)
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.MSG_PREPARE_FAILED, notify=False)
        raise PublicationSubmitError(steps.MSG_PREPARE_FAILED) from exc

    # 投递失败不撤回任务：准备任务没开始的，查询发布状态时兜底超时判失败，用户重试即可。
    await _schedule(tasks.schedule_deployment_prepare, task)


async def _handle_stalled_task(task: PublicationTask) -> None:
    """Queue polling again for a task whose polling stopped, or fail a task that will not end by itself."""
    now = timezone.now()

    if task.deployment_id:
        # 部署超时一般由轮询判。轮询每轮都失败（如配置出错）时走不到那一步，这里兜住，免得项目一直卡在进行中。
        if (task.deploy_submitted_at or task.started_at) <= now - DEPLOY_TIMEOUT:
            minutes = int(DEPLOY_TIMEOUT.total_seconds() // 60)
            await steps.afinish_task(
                task, PublicationTaskStatus.FAILED, error=steps.MSG_DEPLOY_TIMEOUT.format(minutes=minutes)
            )
            return

        # 已提交但很久没人查：轮询消息丢了（投递失败、worker 崩溃），再投一次。
        last_looked_at = task.last_polled_at or task.deploy_submitted_at or task.started_at
        if last_looked_at > now - POLL_STALL_AFTER:
            return

        # 前端每几秒查一次，先按读到的值抢着把 last_polled_at 推到现在，只有抢到的那个请求去投，
        # 否则在轮询恢复前每次查询都会多投一条。推到现在之后，轮询的半周期去重会挡住立即到达的消息，
        # 所以隔一个轮询间隔再投。
        claimed = await (
            PublicationTask.objects.pending()
            .filter(pk=task.pk, last_polled_at=task.last_polled_at)
            .aupdate(last_polled_at=now)
        )
        if claimed:
            logger.warning("Polling of publication task %s stopped at %s; queueing it again", task.pk, last_looked_at)
            await _schedule(tasks.schedule_deployment_poll, task, DEPLOY_POLL_INTERVAL_SECONDS)
        return

    # 发出了部署请求却一直没记下部署 ID：发请求的 worker 中途没了，部署是否生效说不准，不能再发一次。
    # 从发出请求算起，等过一次请求超时再判，免得判掉还在等响应的部署。
    if task.deploy_requested_at:
        # 读到的状态可能已经过时（worker 刚记下部署 ID），所以只在仍没有部署 ID 时判失败。
        if task.deploy_requested_at <= now - DEPLOY_REQUEST_TIMEOUT:
            await steps.afinish_task(
                task, PublicationTaskStatus.FAILED, error=steps.MSG_DEPLOY_UNCERTAIN, before_deployment_submitted=True
            )
        return

    # 很久还没发出部署请求：进程中途没了或队列一直不可用。读到的状态可能已经过时（worker 刚发出部署请求），
    # 所以只在仍未发出请求时判失败。
    if task.started_at <= now - PREPARE_TIMEOUT:
        await steps.afinish_task(
            task, PublicationTaskStatus.FAILED, error=steps.MSG_PREPARE_INTERRUPTED, before_deploy_request=True
        )


async def _schedule(schedule: Callable[..., None], task: PublicationTask, *args: Any) -> None:
    """Queue a Celery task for this publication task."""

    # apply_async 是同步的，会堵住事件循环，放到线程里投。
    try:
        await asyncio.to_thread(schedule, task.pk, *args)
    except Exception:
        # 投递失败不撤回任务。准备任务没开始的，查询时兜底超时判失败；轮询丢了的，下次查询再投。
        logger.exception("Queueing %s for publication task %s failed", schedule.__name__, task.pk)


async def get_publication_state(project: Project) -> PublicationState:
    """Return where the Project stands in the developer center."""
    # 前端在任务进行中会反复来查，顺带给停住的任务一个兜底；兜底可能结束任务，所以之后再读一次。
    active = await PublicationTask.objects.pending().filter(project=project).afirst()
    if active is not None:
        await _handle_stalled_task(active)
        active = await PublicationTask.objects.pending().filter(project=project).afirst()

    binding = await DevCenterAppBinding.objects.filter(project=project).afirst()
    links = None
    if binding is not None:
        links = build_console_links(settings.BKPAAS_URL, binding.app_code, binding.module_name)

    latest = await PublicationTask.objects.filter(project=project).finished().afirst()
    last_failure = None
    if latest is not None and latest.status == PublicationTaskStatus.FAILED:
        last_failure = _build_failure(latest, binding, links)

    # 新任务开始后，上一次的结果属于上一次任务，再展示只会和进行中的状态打架。
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
    successful = PublicationTask.objects.online().filter(project=project)
    latest = await successful.afirst()
    if latest is None:
        return None

    # 开发者中心偶尔拿不到访问地址：更新版本不会改变访问地址，沿用之前记下的。
    url = latest.access_url
    if not url:
        url = await successful.exclude(access_url="").values_list("access_url", flat=True).afirst() or ""

    return OnlineVersion(version_id=latest.version_id, url=url, published_at=latest.finished_at)


def _build_failure(
    task: PublicationTask, binding: DevCenterAppBinding | None, links: ConsoleLinks | None
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
    """Forget the latest result once the owner has seen it."""
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
