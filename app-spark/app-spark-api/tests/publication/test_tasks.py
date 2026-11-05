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

import pytest

from app_spark_api.infras.bk_paas import BkPaaSClient, BkPaaSConfigurationError
from app_spark_api.publication import services, steps, tasks

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(("submitted", "expected"), [(True, [("poll", 1, 3)]), (False, [])])
def test_the_preparation_starts_polling_once_submitted(queued, monkeypatch, submitted, expected):
    async def prepare_once(task_id: int):
        return submitted

    monkeypatch.setattr("app_spark_api.publication.tasks.aprepare_once", prepare_once)

    tasks.prepare_publication_deployment.run(1)

    assert queued == expected


@pytest.mark.parametrize(("countdown", "expected"), [(3, [("poll", 1, 3)]), (None, [])])
def test_the_poll_queues_the_next_one_until_the_end(queued, monkeypatch, countdown, expected):
    async def poll_once(task_id: int):
        return countdown

    monkeypatch.setattr("app_spark_api.publication.tasks.apoll_once", poll_once)

    tasks.poll_publication_deployment.run(1)

    assert queued == expected


async def test_a_missing_configuration_fails_the_task_instead_of_retrying(project, dev_center, monkeypatch):
    task = await services.start_deployment(project, "v2", operator="alice", client_factory=lambda: dev_center)

    def refuse():
        raise BkPaaSConfigurationError("BKPAAS_APIGW_NAME is required to call the developer center")

    monkeypatch.setattr(BkPaaSClient, "from_settings", refuse)

    assert await tasks.apoll_once(task.pk) is None
    assert (await services.get_publication_state(project)).last_failure.error == steps.MSG_NOT_CONFIGURED
