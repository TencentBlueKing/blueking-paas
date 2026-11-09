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

"""The Celery tasks hand over to polling once the deployment is submitted, and poll until it ends."""

import time

import pytest
from asgiref.sync import async_to_sync
from blue_krill.async_utils.poll_task import (
    CallbackResult,
    CallbackStatus,
    PollingMetadata,
    PollingStatus,
    check_status_until_finished,
)

from app_spark_api.infras.bk_paas import BkPaaSClient, BkPaaSConfigurationError, DeploymentResult
from app_spark_api.publication import services, steps, tasks

# 在 queued fixture 换掉它之前取到真的实现，用来验证它怎么启动 poll_task。
from app_spark_api.publication.tasks import schedule_deployment_poll as real_schedule_deployment_poll

pytestmark = pytest.mark.django_db(transaction=True)


def make_poller(task_id: int, last_polling_data: dict | None = None) -> tasks.DeploymentPoller:
    metadata = PollingMetadata(
        retries=0, query_started_at=time.time(), queried_count=0, last_polling_data=last_polling_data
    )
    return tasks.DeploymentPoller({"task_id": task_id}, metadata)


async def make_submitted_task(project, bkpaas):
    task = await services.start_deployment(project, "v2", operator="alice", client_factory=lambda: bkpaas)
    assert await steps.prepare_deployment(task.pk, bkpaas)
    return task


@pytest.mark.parametrize(("submitted", "expected"), [(True, [("poll", 1)]), (False, [])])
def test_the_preparation_starts_polling_once_submitted(queued, monkeypatch, submitted, expected):
    async def prepare_once(task_id: int):
        return submitted

    monkeypatch.setattr("app_spark_api.publication.tasks.aprepare_once", prepare_once)

    tasks.prepare_publication_deployment.run(1)

    assert queued == expected


def test_polling_starts_the_deployment_poller_with_its_handler(monkeypatch):
    sent = []
    monkeypatch.setattr(check_status_until_finished, "delay", lambda *args: sent.append(args))

    real_schedule_deployment_poll(1)

    # poll_task 按类名找轮询器和回调，名字或参数对不上，worker 那边就跑不起来。
    assert sent == [("DeploymentPoller", "DeploymentPollHandler", {"task_id": 1})]


@pytest.mark.parametrize(
    ("outcome", "status", "data"),
    [
        (steps.PollOutcome(finished=False, access_url_polls=1), PollingStatus.DOING, {"access_url_polls": 1}),
        (steps.PollOutcome(finished=True), PollingStatus.DONE, None),
    ],
)
def test_the_poller_carries_progress_until_the_end(monkeypatch, outcome, status, data):
    seen = []

    async def poll_once(task_id: int, access_url_polls: int):
        seen.append(access_url_polls)
        return outcome

    monkeypatch.setattr("app_spark_api.publication.tasks.apoll_once", poll_once)

    result = make_poller(1, {"access_url_polls": 2}).query()

    # 上一轮带过来的轮数交给这一轮，这一轮的再带给下一轮。
    assert seen == [2]
    assert (result.status, result.data) == (status, data)


async def test_the_poller_waits_for_the_access_url_across_rounds(project, bkpaas, monkeypatch):
    task = await make_submitted_task(project, bkpaas)
    bkpaas.queue("get_deployment_result", DeploymentResult("successful"))
    monkeypatch.setattr(BkPaaSClient, "from_settings", lambda: bkpaas)

    first = await tasks.apoll_once(task.pk)
    second = await tasks.apoll_once(task.pk, first.access_url_polls)

    assert (first.finished, first.access_url_polls, second.finished) == (False, 1, True)
    assert (await services.get_publication_state(project)).online.url == "https://apps.example.com/test-project/"


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (CallbackStatus.TIMEOUT, steps.make_deploy_timeout_message()),
        (CallbackStatus.EXCEPTION, steps.MSG_POLL_FAILED),
    ],
)
def test_polling_that_gives_up_fails_the_task(project, bkpaas, status, error):
    task = async_to_sync(make_submitted_task)(project, bkpaas)

    tasks.DeploymentPollHandler().handle(CallbackResult(status=status), make_poller(task.pk))

    task.refresh_from_db()
    assert (task.status, task.error) == ("failed", error)


def test_a_deployment_that_ended_is_left_as_recorded(project, bkpaas):
    task = async_to_sync(make_submitted_task)(project, bkpaas)

    tasks.DeploymentPollHandler().handle(CallbackResult(status=CallbackStatus.NORMAL), make_poller(task.pk))

    task.refresh_from_db()
    assert task.status == "pending"


async def test_a_missing_configuration_fails_the_task_instead_of_retrying(project, bkpaas, monkeypatch):
    task = await services.start_deployment(project, "v2", operator="alice", client_factory=lambda: bkpaas)

    def refuse():
        raise BkPaaSConfigurationError("BKPAAS_APIGW_NAME is required to call the developer center")

    monkeypatch.setattr(BkPaaSClient, "from_settings", refuse)

    assert (await tasks.apoll_once(task.pk)).finished
    assert (await services.get_publication_state(project)).last_failure.error == steps.MSG_NOT_CONFIGURED
