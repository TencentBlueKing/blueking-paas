# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import datetime
import time
from unittest.mock import patch

import arrow
import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus, PollingMetadata, PollingStatus

from paas_wl.cnative.specs.constants import DeployStatus, MResConditionType, MResPhaseType
from paas_wl.cnative.specs.resource import ModelResState
from paas_wl.cnative.specs.tasks import AppModelDeployStatusPoller, DeployStatusHandler
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy, create_condition, create_res_with_conds

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def dp(bk_stag_env, bk_stag_engine_app, bk_user):
    return create_cnative_deploy(bk_stag_env, bk_user, status=DeployStatus.PENDING)


@pytest.fixture
def poller(bk_stag_env, dp):
    """A poller fixture for testing"""
    metadata = PollingMetadata(retries=0, query_started_at=time.time(), queried_count=1)
    return AppModelDeployStatusPoller(params={'deploy_id': dp.id}, metadata=metadata)


class TestAppModelDeployStatusPoller:
    @patch('paas_wl.cnative.specs.tasks.get_mres_from_cluster', return_value=create_res_with_conds([]))
    def test_pending(self, mocker, dp, poller):
        ret = poller.query()
        assert ret.status == PollingStatus.DOING
        dp.refresh_from_db()
        assert dp.status == DeployStatus.PENDING

    @patch(
        'paas_wl.cnative.specs.tasks.get_mres_from_cluster',
        return_value=create_res_with_conds([create_condition(MResConditionType.APP_AVAILABLE)]),
    )
    def test_progressing(self, mocker, dp, poller):
        ret = poller.query()
        assert ret.status == PollingStatus.DOING
        dp.refresh_from_db()
        assert dp.status == DeployStatus.PROGRESSING

    @patch(
        'paas_wl.cnative.specs.tasks.get_mres_from_cluster',
        return_value=create_res_with_conds(
            [create_condition(MResConditionType.APP_AVAILABLE, "True")], MResPhaseType.AppRunning
        ),
    )
    def test_stable(self, mocker, poller):
        ret = poller.query()
        assert ret.status == PollingStatus.DONE
        assert 'state' in ret.data
        assert 'last_update' in ret.data


class TestDeployStatusHandler:
    def test_handle_failed(self, dp, poller):
        DeployStatusHandler().handle(result=CallbackResult(status=CallbackStatus.EXCEPTION), poller=poller)
        dp.refresh_from_db()
        assert dp.status == DeployStatus.ERROR
        assert dp.reason == 'internal'

    def test_handle_ready(self, dp, poller):
        DeployStatusHandler().handle(
            result=CallbackResult(
                status=CallbackStatus.NORMAL,
                data={
                    'state': ModelResState(DeployStatus.READY, 'ready', 'foo ready'),
                    'last_update': arrow.get('2020-10-10').datetime,
                },
            ),
            poller=poller,
        )

        dp.refresh_from_db()
        # Assert deploy has been updated
        assert dp.status == DeployStatus.READY
        assert dp.reason == 'ready'
        assert dp.message == 'foo ready'
        assert dp.last_transition_time.date() == datetime.date(2020, 10, 10)
