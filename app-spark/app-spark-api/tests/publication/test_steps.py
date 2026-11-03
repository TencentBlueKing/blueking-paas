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

"""The request creates the application; Celery packs, uploads, submits and polls; the result is recorded once."""

from datetime import timedelta

import httpx2
import pytest
from django.db import IntegrityError
from django.http import Http404
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.infras.bk_paas import BkPaaSApiError, DeploymentResult
from app_spark_api.publication import services, steps
from app_spark_api.publication.constants import PublicationTaskStatus
from app_spark_api.publication.exceptions import PublicationAppNameInvalidError, PublicationSubmitError
from app_spark_api.publication.models import DevCenterAppBinding, PublicationTask
from app_spark_api.publication.packaging import SourcePackagingError
from tests.publication.conftest import CONSOLE_URL

pytestmark = pytest.mark.django_db(transaction=True)

APP_URL = f"{CONSOLE_URL}/developer-center/apps/test-project"


async def start(project, dev_center, version_id: str = "v2") -> PublicationTask:
    return await services.start_deployment(project, version_id, operator="alice", client_factory=lambda: dev_center)


async def prepare(task: PublicationTask, dev_center) -> PublicationTask:
    await steps.prepare_deployment(task.pk, dev_center)
    await task.arefresh_from_db()
    return task


async def poll_until_done(task: PublicationTask, dev_center) -> PublicationTask:
    """Poll the way Celery would, without waiting between polls."""
    for _ in range(20):
        # 测试里不等轮询间隔，把上一轮的时间清掉，免得被「刚查过」拦下。
        await PublicationTask.objects.filter(pk=task.pk).aupdate(last_polled_at=None)
        if await steps.poll_deployment(task.pk, dev_center) is None:
            await task.arefresh_from_db()
            return task

    raise AssertionError("the deployment did not end within 20 polls")


async def publish(project, dev_center, version_id: str = "v2") -> PublicationTask:
    task = await prepare(await start(project, dev_center, version_id), dev_center)
    return await poll_until_done(task, dev_center)


async def test_a_first_deployment_goes_from_the_request_through_celery_to_online(project, dev_center, queued):
    task = await start(project, dev_center)

    # 请求里只建应用：应用 ID 就是项目 ID；名称默认取项目名称，按开发者中心的规则去掉空格后发出去。
    (create,) = dev_center.called("create_app")
    assert (create["code"], create["name"], create["operator"]) == ("test-project", "TestProject", "alice")
    assert (task.stage, queued) == ("packaging", [("prepare", task.pk)])

    assert await steps.prepare_deployment(task.pk, dev_center)
    await task.arefresh_from_db()
    assert [name for name, _ in dev_center.calls][1:] == ["upload_package_via_link", "deploy"]
    assert (task.stage, task.deployment_id) == ("deploying", "d-1")

    await poll_until_done(task, dev_center)

    state = await services.get_publication_state(project)
    assert state.task is None
    assert (state.online.version_id, state.online.url) == ("v2", "https://apps.example.com/test-project/")
    assert (state.unseen_result.status, state.last_failure) == ("successful", None)


async def test_an_update_reuses_the_app_and_keeps_the_url(project, dev_center):
    await publish(project, dev_center, "v1")
    dev_center.calls.clear()
    # 开发者中心这次没给访问地址：更新版本不会改变访问地址，沿用之前的。
    for _ in range(4):
        dev_center.queue("get_deployment_result", DeploymentResult("successful"))

    task = await publish(project, dev_center, "v2")

    state = await services.get_publication_state(project)
    assert task.is_update
    assert dev_center.called("create_app") == []
    assert (state.online.version_id, state.online.url) == ("v2", "https://apps.example.com/test-project/")


async def test_a_failed_update_leaves_the_online_version_alone(project, dev_center):
    await publish(project, dev_center, "v1")
    dev_center.queue("get_deployment_result", DeploymentResult("failed", error_detail="Procfile error"))

    await publish(project, dev_center, "v2")

    state = await services.get_publication_state(project)
    assert state.online.version_id == "v1"
    assert state.unseen_result.status == "failed"
    assert (state.last_failure.is_update, state.last_failure.error) == (True, "Procfile error")
    assert state.last_failure.detail_url == f"{APP_URL}/deployments/history?logId=d-1"

    # 确认看过之后，结果不再提醒，失败记录留着。
    await services.clear_unseen_result(project)
    state = await services.get_publication_state(project)
    assert (state.unseen_result, state.last_failure.error) == (None, "Procfile error")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (BkPaaSApiError(400, "应用 ID 已存在", fields_detail={"code": ["已存在"]}), "应用 ID 已存在"),
        (BkPaaSApiError(403, "x", code="APP_SPARK_APP_REQUIRED"), steps.MSG_APP_NOT_MANAGED),
        (BkPaaSApiError(403, "x", code="APP_SPARK_MODULE_REQUIRED"), steps.MSG_MODULE_NOT_DEFAULT),
        (BkPaaSApiError(403, "x", code="SYSAPI_CLIENT_PERM_DENIED"), steps.MSG_NOT_AUTHORIZED),
        (httpx2.ReadTimeout("timed out"), steps.MSG_DEV_CENTER_UNAVAILABLE),
    ],
)
async def test_failing_to_create_the_app_is_told_in_the_response(project, dev_center, queued, error, message):
    dev_center.queue("create_app", error)

    with pytest.raises(PublicationSubmitError, match=message):
        await start(project, dev_center)

    # 用户在响应里已经看到原因：项目放开、留下失败记录，但不再提醒一次，也不投递准备任务。
    state = await services.get_publication_state(project)
    assert (state.task, state.unseen_result, state.last_failure.error) == (None, None, message)
    assert not await DevCenterAppBinding.objects.filter(project=project).aexists()
    assert queued == []


@pytest.mark.parametrize(
    ("project_name", "expected"),
    [
        ("Spark App", "SparkApp"),
        # 项目名称全是开发者中心不认的字符时退回 ID。
        ("!!!", "test-project"),
    ],
)
async def test_the_default_app_name_comes_from_the_project_name(project, dev_center, project_name, expected):
    await Project.objects.filter(pk=project.pk).aupdate(name=project_name)
    await project.arefresh_from_db()

    await start(project, dev_center)

    assert dev_center.called("create_app")[0]["name"] == expected


async def test_a_given_app_name_is_sent_after_filtering(project, dev_center):
    await services.start_deployment(
        project, "v2", operator="alice", app_name="Spa rk", client_factory=lambda: dev_center
    )

    assert dev_center.called("create_app")[0]["name"] == "Spark"


async def test_an_app_name_without_usable_characters_is_refused_up_front(project, dev_center):
    with pytest.raises(PublicationAppNameInvalidError):
        await services.start_deployment(
            project, "v2", operator="alice", app_name="!!!", client_factory=lambda: dev_center
        )

    assert dev_center.calls == []
    assert not await PublicationTask.objects.filter(project=project).aexists()


async def test_a_project_deleted_before_the_task_is_created_is_not_published(project, dev_center):
    await Project.objects.asoft_delete(project.pk)

    with pytest.raises(Http404):
        await start(project, dev_center)

    assert dev_center.calls == []


async def test_an_app_created_but_not_recorded_is_told_in_the_response(project, dev_center, monkeypatch):
    def fail_to_record(project, app):
        raise IntegrityError("Duplicate entry for key project_id")

    monkeypatch.setattr("app_spark_api.publication.steps._record_app", fail_to_record)

    # 应用已在开发者中心建好：说清楚是哪个应用，任务当场结束，项目不被挂住。
    with pytest.raises(PublicationSubmitError, match="test-project"):
        await start(project, dev_center)

    assert (await services.get_publication_state(project)).task is None


@pytest.mark.parametrize(
    ("method", "error", "message"),
    [
        ("upload_package_via_link", BkPaaSApiError(400, "源码包下载失败"), "源码包下载失败"),
        ("deploy", BkPaaSApiError(400, "已有部署在进行"), "已有部署在进行"),
        # 部署请求超时或 5xx：可能已经生效，不重发，让用户去部署记录里确认。
        ("deploy", httpx2.ReadTimeout("timed out"), steps.MSG_DEPLOY_UNCERTAIN),
        ("deploy", BkPaaSApiError(502, "bad gateway"), steps.MSG_DEPLOY_UNCERTAIN),
    ],
)
async def test_a_failure_while_preparing_is_left_for_the_owner_to_see(project, dev_center, method, error, message):
    dev_center.queue(method, error)
    task = await start(project, dev_center)

    assert not await steps.prepare_deployment(task.pk, dev_center)

    state = await services.get_publication_state(project)
    assert len(dev_center.called("deploy")) <= 1
    assert (state.task, state.unseen_result.status, state.last_failure.error) == (None, "failed", message)
    # 没拿到部署 ID，指向部署管理页。
    assert state.last_failure.detail_url == f"{APP_URL}/deployments/prod"


async def test_a_packaging_failure_is_left_for_the_owner_to_see(project, dev_center, monkeypatch):
    async def fail_to_pack(project, version_id):
        raise SourcePackagingError("代码仓库里找不到版本")

    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", fail_to_pack)

    await prepare(await start(project, dev_center), dev_center)

    assert (await services.get_publication_state(project)).last_failure.error == "代码仓库里找不到版本"
    assert dev_center.called("upload_package_via_link") == []


async def test_a_redelivered_preparation_is_dropped(project, dev_center):
    task = await start(project, dev_center)

    assert await steps.prepare_deployment(task.pk, dev_center)
    # 重复投递、worker 崩溃后的重投都撞上认领，不会再打包、再部署。
    assert not await steps.prepare_deployment(task.pk, dev_center)
    assert len(dev_center.called("deploy")) == 1


async def test_a_task_failed_while_packing_is_not_deployed(project, dev_center, monkeypatch):
    task = await start(project, dev_center)
    pack = steps.packaging.apackage_version

    async def pack_too_slowly(project, version_id):
        # 打包太慢，期间被兜底判了失败。
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.MSG_PREPARE_INTERRUPTED)
        return await pack(project, version_id)

    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", pack_too_slowly)

    assert not await steps.prepare_deployment(task.pk, dev_center)
    # 打包回来发现任务已经结束，不再上传，更不会部署。
    assert dev_center.called("upload_package_via_link") == []
    assert dev_center.called("deploy") == []


async def test_a_deployment_submitted_after_the_task_ended_is_not_polled(project, dev_center, monkeypatch):
    task = await start(project, dev_center)
    deploy = dev_center.deploy

    async def deploy_while_judged_failed(**kwargs):
        # 部署请求在路上时任务被并发判了失败。
        await PublicationTask.objects.filter(pk=task.pk).aupdate(status=PublicationTaskStatus.FAILED)
        return await deploy(**kwargs)

    monkeypatch.setattr(dev_center, "deploy", deploy_while_judged_failed)

    assert not await steps.prepare_deployment(task.pk, dev_center)

    # 不轮询，但留下部署 ID，失败详情能直接指向这次部署。
    await task.arefresh_from_db()
    assert (task.status, task.deployment_id) == ("failed", "d-1")


@pytest.mark.parametrize(
    "hiccup",
    [
        pytest.param(BkPaaSApiError(502, "bad gateway"), id="server-error"),
        pytest.param(BkPaaSApiError(429, "slow down"), id="throttled"),
        pytest.param(httpx2.ConnectError("refused"), id="network"),
        pytest.param(DeploymentResult("queued"), id="unknown-status"),
        # 部署成功但还没给访问地址：多查一轮，地址是要分享给同事的。
        pytest.param(DeploymentResult("successful"), id="no-url-yet"),
    ],
)
async def test_a_hiccup_while_polling_is_waited_out(project, dev_center, hiccup):
    dev_center.queue("get_deployment_result", hiccup)

    task = await publish(project, dev_center)

    assert task.status == PublicationTaskStatus.SUCCESSFUL
    assert len(dev_center.called("get_deployment_result")) == 2
    assert (await services.get_publication_state(project)).online.url == "https://apps.example.com/test-project/"


async def test_a_deployment_that_never_ends_times_out(project, dev_center):
    task = await prepare(await start(project, dev_center), dev_center)
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deploy_submitted_at=timezone.now() - timedelta(hours=1))
    dev_center.queue("get_deployment_result", DeploymentResult("pending"))

    await poll_until_done(task, dev_center)

    state = await services.get_publication_state(project)
    assert state.last_failure.error == steps.MSG_DEPLOY_TIMEOUT.format(minutes=15)


async def test_a_duplicate_poll_is_dropped_and_the_result_is_recorded_once(project, dev_center):
    task = await prepare(await start(project, dev_center), dev_center)
    dev_center.queue("get_deployment_result", DeploymentResult("pending"))

    # 重复投递的消息前后脚到达：任务还在进行中，第二条被「刚查过」拦下，不会再去问开发者中心。
    assert await steps.poll_deployment(task.pk, dev_center) == 3
    assert await steps.poll_deployment(task.pk, dev_center) is None
    assert len(dev_center.called("get_deployment_result")) == 1

    task = await poll_until_done(task, dev_center)

    # 两条轮询都看到了结束，也只有先到的那条记结果。
    assert not await steps.afinish_task(task, PublicationTaskStatus.FAILED, error="late")
    assert (await services.get_publication_state(project)).online.version_id == "v2"


@pytest.mark.parametrize(
    ("stalled", "expected"),
    [
        # 时间字段写成「多久以前」，在用例里按当前时间换算；在这里求值会被固定在收集用例的那一刻。
        # 准备任务开始后 worker 没了，或者准备消息丢了：不重做，判失败。
        pytest.param({"started_at": timedelta(minutes=11)}, steps.MSG_PREPARE_INTERRUPTED, id="preparation-died"),
        # 发出部署请求后 worker 没了：部署是否生效说不准，判失败让用户去确认。
        pytest.param(
            {"started_at": timedelta(minutes=11), "deploy_requested_at": timedelta(minutes=3)},
            steps.MSG_DEPLOY_UNCERTAIN,
            id="deploy-request-died",
        ),
        # 部署请求刚发出、还在等响应：即使发起已超过 10 分钟也不判。
        pytest.param(
            {"started_at": timedelta(minutes=11), "deploy_requested_at": timedelta(seconds=30)},
            None,
            id="deploy-request-in-flight",
        ),
        # 轮询一直失败、走不到超时判断：兜底按部署超时判失败。
        pytest.param(
            {"deployment_id": "d-1", "deploy_submitted_at": timedelta(minutes=16)},
            steps.MSG_DEPLOY_TIMEOUT.format(minutes=15),
            id="deploy-timed-out",
        ),
        # 还没到超时：不动它。
        pytest.param({"started_at": timedelta(minutes=5)}, None, id="still-preparing"),
        # 轮询消息丢了：隔一个轮询间隔再投一次轮询。
        pytest.param({"deployment_id": "d-1", "last_polled_at": timedelta(minutes=5)}, ("poll", 3), id="poll-lost"),
    ],
)
async def test_reading_the_state_handles_a_stalled_task(project, dev_center, queued, stalled, expected):
    """expected is the failure recorded, the message queued again, or None when the task is left alone."""
    task = await start(project, dev_center)
    now = timezone.now()
    fields = {key: now - value if isinstance(value, timedelta) else value for key, value in stalled.items()}
    await PublicationTask.objects.filter(pk=task.pk).aupdate(**fields)
    queued.clear()

    state = await services.get_publication_state(project)

    if isinstance(expected, str):
        assert (state.task, state.last_failure.error, queued) == (None, expected, [])
    else:
        assert state.task is not None
        assert queued == ([] if expected is None else [(expected[0], task.pk, *expected[1:])])


async def test_a_stalled_poll_is_queued_again_only_once(project, dev_center, queued):
    task = await start(project, dev_center)
    stalled_at = timezone.now() - timedelta(minutes=5)
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deployment_id="d-1", last_polled_at=stalled_at)
    queued.clear()

    # 前端每几秒查一次：轮询恢复之前，只有第一次查询会补投。
    await services.get_publication_state(project)
    await services.get_publication_state(project)

    assert queued == [("poll", task.pk, 3)]


async def test_a_stale_read_does_not_fail_a_task_whose_deployment_was_just_submitted(project, dev_center):
    task = await start(project, dev_center)
    # 兜底读到的还没有部署 ID，worker 随后记下了它。
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deploy_requested_at=timezone.now(), deployment_id="d-1")

    assert not await steps.afinish_task(
        task, PublicationTaskStatus.FAILED, error=steps.MSG_DEPLOY_UNCERTAIN, before_deployment_submitted=True
    )


async def test_a_stale_read_does_not_fail_a_task_whose_deployment_was_just_requested(project, dev_center):
    task = await start(project, dev_center)
    # 兜底读到的是旧状态，worker 随后发出了部署请求。
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deploy_requested_at=timezone.now())

    assert not await steps.afinish_task(
        task, PublicationTaskStatus.FAILED, error=steps.MSG_PREPARE_INTERRUPTED, before_deploy_request=True
    )
