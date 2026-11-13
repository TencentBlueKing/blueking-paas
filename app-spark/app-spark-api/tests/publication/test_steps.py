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
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.infras.bk_paas import (
    AppBasicInfoValidation,
    AppFieldError,
    BkPaaSApiError,
    DeploymentResult,
)
from app_spark_api.publication import app_name, packaging, services, steps
from app_spark_api.publication.constants import PublicationTaskStatus
from app_spark_api.publication.exceptions import (
    PublicationAppNameConflictError,
    PublicationAppNameInvalidError,
    PublicationProjectGoneError,
    PublicationSubmitError,
)
from app_spark_api.publication.models import BkPaaSAppBinding, PublicationTask
from app_spark_api.publication.packaging import SourcePackagingError
from tests.publication.conftest import CONSOLE_URL

pytestmark = pytest.mark.django_db(transaction=True)

APP_URL = f"{CONSOLE_URL}/developer-center/apps/test-project"


async def start(project, bkpaas, version_id: str = "v2") -> PublicationTask:
    return await services.start_deployment(project, version_id, operator="alice", client_factory=lambda: bkpaas)


async def prepare(task: PublicationTask, bkpaas) -> PublicationTask:
    await steps.prepare_deployment(task.pk, bkpaas)
    await task.arefresh_from_db()
    return task


async def poll_until_done(task: PublicationTask, bkpaas) -> PublicationTask:
    """Poll the way the poller would, carrying each round's progress into the next, without waiting between polls."""
    access_url_polls = 0
    for _ in range(20):
        outcome = await steps.poll_deployment(task.pk, bkpaas, access_url_polls=access_url_polls)
        if outcome.finished:
            await task.arefresh_from_db()
            return task

        access_url_polls = outcome.access_url_polls

    raise AssertionError("the deployment did not end within 20 polls")


async def publish(project, bkpaas, version_id: str = "v2") -> PublicationTask:
    task = await prepare(await start(project, bkpaas, version_id), bkpaas)
    return await poll_until_done(task, bkpaas)


async def test_a_first_deployment_goes_from_the_request_through_celery_to_online(project, bkpaas, queued):
    task = await start(project, bkpaas)

    # 请求里先校验再建应用：应用 ID 就是项目 ID；名称默认取项目名称，按开发者中心的规则去掉空格后发出去。
    (validate,) = bkpaas.called("validate_app_basic_info")
    (create,) = bkpaas.called("create_app")
    assert (validate["code"], validate["name"]) == ("test-project", "TestProject")
    assert (create["code"], create["name"], create["operator"]) == ("test-project", "TestProject", "alice")
    assert (task.stage, queued) == ("packaging", [("prepare", task.pk)])

    assert await steps.prepare_deployment(task.pk, bkpaas)
    await task.arefresh_from_db()
    assert [name for name, _ in bkpaas.calls][2:] == ["upload_package_via_link", "deploy"]
    assert (task.stage, task.deployment_id) == ("deploying", "d-1")

    await poll_until_done(task, bkpaas)

    state = await services.get_publication_state(project)
    assert state.task is None
    assert (state.online.version_id, state.online.url) == ("v2", "https://apps.example.com/test-project/")
    assert (state.unseen_result.status, state.last_failure) == ("successful", None)


async def test_an_update_reuses_the_app_and_keeps_the_url(project, bkpaas):
    await publish(project, bkpaas, "v1")
    bkpaas.calls.clear()
    # 开发者中心这次没给访问地址：更新版本不会改变访问地址，沿用之前的。
    for _ in range(4):
        bkpaas.queue("get_deployment_result", DeploymentResult("successful"))

    task = await publish(project, bkpaas, "v2")

    state = await services.get_publication_state(project)
    assert task.is_update
    assert bkpaas.called("create_app") == []
    assert (state.online.version_id, state.online.url) == ("v2", "https://apps.example.com/test-project/")


async def test_a_failed_update_leaves_the_online_version_alone(project, bkpaas):
    await publish(project, bkpaas, "v1")
    bkpaas.queue("get_deployment_result", DeploymentResult("failed", error_detail="Procfile error"))

    await publish(project, bkpaas, "v2")

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
        (httpx2.ReadTimeout("timed out"), steps.MSG_BKPAAS_UNAVAILABLE),
    ],
)
async def test_failing_to_create_the_app_is_told_in_the_response(project, bkpaas, queued, error, message):
    bkpaas.queue("create_app", error)

    with pytest.raises(PublicationSubmitError, match=message):
        await start(project, bkpaas)

    # 用户在响应里已经看到原因：项目放开、留下失败记录，但不再提醒一次，也不投递准备任务。
    state = await services.get_publication_state(project)
    assert (state.task, state.unseen_result, state.last_failure.error) == (None, None, message)
    assert not await BkPaaSAppBinding.objects.filter(project=project).aexists()
    assert queued == []


@pytest.mark.parametrize(
    ("project_name", "expected"),
    [
        ("Spark App", "SparkApp"),
        # 项目名称全是开发者中心不认的字符时退回 ID。
        ("!!!", "test-project"),
    ],
)
async def test_the_default_app_name_comes_from_the_project_name(project, bkpaas, project_name, expected):
    await Project.objects.filter(pk=project.pk).aupdate(name=project_name)
    await project.arefresh_from_db()

    await start(project, bkpaas)

    assert bkpaas.called("create_app")[0]["name"] == expected


async def test_a_given_app_name_is_sent_after_filtering(project, bkpaas):
    await services.start_deployment(project, "v2", operator="alice", app_name="Spa rk", client_factory=lambda: bkpaas)

    assert bkpaas.called("create_app")[0]["name"] == "Spark"


async def test_an_app_name_without_usable_characters_is_refused_up_front(project, bkpaas):
    with pytest.raises(PublicationAppNameInvalidError):
        await services.start_deployment(project, "v2", operator="alice", app_name="!!!", client_factory=lambda: bkpaas)

    assert bkpaas.calls == []
    assert not await PublicationTask.objects.filter(project=project).aexists()


async def test_a_taken_app_name_is_refused_before_any_task(project, bkpaas, queued):
    bkpaas.queue(
        "validate_app_basic_info",
        AppBasicInfoValidation(None, AppFieldError("unique", "名称已存在")),
    )

    with pytest.raises(PublicationAppNameConflictError):
        await start(project, bkpaas)

    # 重名时用户改个名字再发就好：不建任务，所以也不留失败记录。
    assert bkpaas.called("create_app") == []
    assert not await PublicationTask.objects.filter(project=project).aexists()
    assert queued == []


async def test_a_refused_app_id_is_told_before_any_task(project, bkpaas):
    # 名称也重名时先说应用 ID：用户改不了它，只让改名会白改一次。
    bkpaas.queue(
        "validate_app_basic_info",
        AppBasicInfoValidation(AppFieldError("unique", "应用 ID 已存在"), AppFieldError("unique", "名称已存在")),
    )

    with pytest.raises(PublicationSubmitError, match="应用 ID 已存在"):
        await start(project, bkpaas)

    assert not await PublicationTask.objects.filter(project=project).aexists()


async def test_an_unanswered_validation_leaves_the_judgement_to_app_creation(project, bkpaas):
    bkpaas.queue("validate_app_basic_info", httpx2.ConnectError("refused"))

    task = await start(project, bkpaas)

    assert task.stage == "packaging"
    assert len(bkpaas.called("create_app")) == 1


async def test_a_name_taken_meanwhile_is_answered_as_a_conflict(project, bkpaas, queued):
    """校验时名称还空着，创建时被别人抢先用了。"""
    bkpaas.queue("create_app", BkPaaSApiError(400, "名称已存在", fields_detail={"name": ["已存在"]}))

    with pytest.raises(PublicationAppNameConflictError):
        await start(project, bkpaas)

    # 任务当场结束，不主动弹出失败结果，用户在面板上改名重发。
    state = await services.get_publication_state(project)
    assert (state.task, state.unseen_result) == (None, None)
    assert state.last_failure is not None
    assert state.last_failure.error == steps.MSG_APP_NAME_TAKEN.format(name="TestProject")
    assert queued == []


@pytest.mark.parametrize(
    ("name", "answer", "expected"),
    [
        ("Spa rk", AppBasicInfoValidation(None, None), ("Spark", None, None)),
        (
            "Spark",
            AppBasicInfoValidation(None, AppFieldError("unique", "名称已存在")),
            ("Spark", "unique", "名称已存在"),
        ),
    ],
)
async def test_validating_a_name_reports_what_would_be_used(project, bkpaas, name, answer, expected):
    bkpaas.queue("validate_app_basic_info", answer)

    validation = await app_name.validate_app_name(project, name)

    assert (validation.name, validation.problem, validation.message) == expected
    # 只问名称，不带应用 ID。
    assert bkpaas.called("validate_app_basic_info") == [{"name": expected[0]}]


async def test_validating_a_name_without_usable_characters_does_not_ask(project, bkpaas):
    validation = await app_name.validate_app_name(project, "!!!")

    assert (validation.name, validation.problem, validation.is_available) == ("", "invalid", False)
    assert bkpaas.calls == []


async def test_validating_a_name_when_the_developer_center_is_down_says_so(project, bkpaas):
    bkpaas.queue("validate_app_basic_info", httpx2.ConnectError("refused"))

    with pytest.raises(steps.PublicationStepError, match=steps.MSG_BKPAAS_UNAVAILABLE):
        await app_name.validate_app_name(project, "Spark")


async def test_a_project_deleted_before_the_task_is_created_is_not_published(project, bkpaas):
    await Project.objects.asoft_delete(project.pk)

    with pytest.raises(PublicationProjectGoneError):
        await start(project, bkpaas)

    # 建任务前只读地校验过名称，应用没有建。
    assert bkpaas.called("create_app") == []


async def test_an_app_created_but_not_recorded_is_told_in_the_response(project, bkpaas, monkeypatch):
    def fail_to_record(project, app):
        raise IntegrityError("Duplicate entry for key project_id")

    monkeypatch.setattr("app_spark_api.publication.steps.binding._record_app", fail_to_record)

    # 应用已在开发者中心建好：说清楚是哪个应用，任务当场结束，项目不被挂住。
    with pytest.raises(PublicationSubmitError, match="test-project"):
        await start(project, bkpaas)

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
async def test_a_failure_while_preparing_is_left_for_the_owner_to_see(project, bkpaas, method, error, message):
    bkpaas.queue(method, error)
    task = await start(project, bkpaas)

    assert not await steps.prepare_deployment(task.pk, bkpaas)

    state = await services.get_publication_state(project)
    assert len(bkpaas.called("deploy")) <= 1
    assert (state.task, state.unseen_result.status, state.last_failure.error) == (None, "failed", message)
    # 没拿到部署 ID，指向部署管理页。
    assert state.last_failure.detail_url == f"{APP_URL}/deployments/prod"


async def test_a_packaging_failure_is_left_for_the_owner_to_see(project, bkpaas, monkeypatch):
    async def fail_to_pack(project, version_id):
        raise SourcePackagingError("代码仓库里找不到版本")

    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", fail_to_pack)

    await prepare(await start(project, bkpaas), bkpaas)

    assert (await services.get_publication_state(project)).last_failure.error == "代码仓库里找不到版本"
    assert bkpaas.called("upload_package_via_link") == []


async def test_a_redelivered_preparation_is_dropped(project, bkpaas):
    task = await start(project, bkpaas)

    assert await steps.prepare_deployment(task.pk, bkpaas)
    # 重复投递、worker 崩溃后的重投都撞上认领，不会再打包、再部署。
    assert not await steps.prepare_deployment(task.pk, bkpaas)
    assert len(bkpaas.called("deploy")) == 1


async def test_a_task_failed_while_packing_is_not_deployed(project, bkpaas, monkeypatch):
    task = await start(project, bkpaas)
    pack = packaging.apackage_version

    async def pack_too_slowly(project, version_id):
        # 打包太慢，期间被兜底判了失败。
        await steps.afinish_task(task, PublicationTaskStatus.FAILED, error=steps.MSG_PREPARE_INTERRUPTED)
        return await pack(project, version_id)

    monkeypatch.setattr("app_spark_api.publication.packaging.apackage_version", pack_too_slowly)

    assert not await steps.prepare_deployment(task.pk, bkpaas)
    # 打包回来发现任务已经结束，不再上传，更不会部署。
    assert bkpaas.called("upload_package_via_link") == []
    assert bkpaas.called("deploy") == []


async def test_a_deployment_submitted_after_the_task_ended_is_not_polled(project, bkpaas, monkeypatch):
    task = await start(project, bkpaas)
    deploy = bkpaas.deploy

    async def deploy_while_judged_failed(**kwargs):
        # 部署请求在路上时任务被并发判了失败。
        await PublicationTask.objects.filter(pk=task.pk).aupdate(status=PublicationTaskStatus.FAILED)
        return await deploy(**kwargs)

    monkeypatch.setattr(bkpaas, "deploy", deploy_while_judged_failed)

    assert not await steps.prepare_deployment(task.pk, bkpaas)

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
async def test_a_hiccup_while_polling_is_waited_out(project, bkpaas, hiccup):
    bkpaas.queue("get_deployment_result", hiccup)

    task = await publish(project, bkpaas)

    assert task.status == PublicationTaskStatus.SUCCESSFUL
    assert len(bkpaas.called("get_deployment_result")) == 2
    assert (await services.get_publication_state(project)).online.url == "https://apps.example.com/test-project/"


async def test_a_result_seen_by_two_polls_is_recorded_once(project, bkpaas):
    task = await publish(project, bkpaas)
    polls = len(bkpaas.called("get_deployment_result"))

    # 重复投递的两条轮询都看到了结束，也只有先到的那条记结果；后到的发现任务已结束，不再去问开发者中心。
    assert not await steps.afinish_task(task, PublicationTaskStatus.FAILED, error="late")
    assert (await steps.poll_deployment(task.pk, bkpaas)).finished
    assert len(bkpaas.called("get_deployment_result")) == polls
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
        # 轮询停掉了（投递失败、消息丢了），没人判超时：兜底按部署超时判失败。
        pytest.param(
            {"deployment_id": "d-1", "deploy_submitted_at": timedelta(minutes=16)},
            steps.make_deploy_timeout_message(),
            id="deploy-timed-out",
        ),
        # 部署还没到超时：交给轮询，不动它。
        pytest.param(
            {"deployment_id": "d-1", "deploy_submitted_at": timedelta(minutes=5)}, None, id="still-deploying"
        ),
        # 还没到超时：不动它。
        pytest.param({"started_at": timedelta(minutes=5)}, None, id="still-preparing"),
    ],
)
async def test_reading_the_state_handles_a_stalled_task(project, bkpaas, queued, stalled, expected):
    """expected is the failure recorded, or None when the task is left alone."""
    task = await start(project, bkpaas)
    now = timezone.now()
    fields = {key: now - value if isinstance(value, timedelta) else value for key, value in stalled.items()}
    await PublicationTask.objects.filter(pk=task.pk).aupdate(**fields)
    queued.clear()

    state = await services.get_publication_state(project)

    if expected is None:
        assert state.task is not None
    else:
        assert (state.task, state.last_failure.error) == (None, expected)

    # 兜底只判失败，不重投任何消息。
    assert queued == []


async def test_a_stale_read_does_not_fail_a_task_whose_deployment_was_just_submitted(project, bkpaas):
    task = await start(project, bkpaas)
    # 兜底读到的还没有部署 ID，worker 随后记下了它。
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deploy_requested_at=timezone.now(), deployment_id="d-1")

    assert not await steps.afinish_task(
        task,
        PublicationTaskStatus.FAILED,
        error=steps.MSG_DEPLOY_UNCERTAIN,
        guard=steps.FinishGuard.BEFORE_DEPLOYMENT_SUBMITTED,
    )


async def test_a_stale_read_does_not_fail_a_task_whose_deployment_was_just_requested(project, bkpaas):
    task = await start(project, bkpaas)
    # 兜底读到的是旧状态，worker 随后发出了部署请求。
    await PublicationTask.objects.filter(pk=task.pk).aupdate(deploy_requested_at=timezone.now())

    assert not await steps.afinish_task(
        task,
        PublicationTaskStatus.FAILED,
        error=steps.MSG_PREPARE_INTERRUPTED,
        guard=steps.FinishGuard.BEFORE_DEPLOY_REQUEST,
    )
