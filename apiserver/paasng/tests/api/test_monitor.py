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
import random
from datetime import datetime, timedelta
from unittest import mock

import pytest

from paasng.infras.bkmonitorv3.constants import SpaceType
from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from tests.utils.mocks.bkmonitor import StubBKMonitorClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def bk_monitor_space(bk_app):
    return BKMonitorSpace.objects.create(
        application=bk_app,
        id=40000,
        space_type_id=SpaceType.SAAS,
        space_id='100',
        space_name='蓝鲸应用-test',
        extra_info={'test': 'test'},
    )


class TestListAlertsView:
    @mock.patch("paasng.infras.bkmonitorv3.client.BkMonitorClient", new=StubBKMonitorClient)
    def test_list_alerts(self, api_client, bk_app, bk_monitor_space):
        resp = api_client.post(
            f'/api/monitor/applications/{bk_app.code}/alerts/',
            data={
                'start_time': (datetime.now() - timedelta(minutes=random.randint(1, 30))).strftime(
                    '%Y-%m-%d %H:%M:%S'
                ),
                'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            },
        )
        assert len(resp.data) == 3
        assert resp.data[0]['status'] in ['ABNORMAL', 'CLOSED', 'RECOVERED']
        assert len(resp.data[0]['receivers']) == 2


class TestAlarmStrategiesView:
    @mock.patch("paasng.infras.bkmonitorv3.client.BkMonitorClient", new=StubBKMonitorClient)
    def test_list_alarm_strategies(self, api_client, bk_app, bk_monitor_space):
        resp = api_client.post(
            f'/api/monitor/applications/{bk_app.code}/alarm_strategies/',
        )
        alarm_strategies = resp.data['strategy_config_list']
        assert len(alarm_strategies) == 3
        assert alarm_strategies[0]['is_enabled'] in [True, False]
