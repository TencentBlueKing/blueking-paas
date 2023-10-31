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

from tests.utils.mocks.bkmonitor import StubBKMonitorClient

pytestmark = pytest.mark.django_db


class TestListAlertsView:
    @mock.patch("paasng.infras.bkmonitorv3.client.BkMonitorClient", new=StubBKMonitorClient)
    def test_list_alerts(self, api_client, bk_app):
        resp = api_client.post(
            f'/api/monitor/applications/{bk_app.code}/alerts/',
            data={
                'start_time': (datetime.now() - timedelta(minutes=random.randint(1, 30))).strftime(
                    '%Y-%m-%d %H:%M:%S'
                ),
                'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            },
        )
        alerts = resp.data['alerts']
        assert len(alerts) == 3
        assert alerts[0]['status'] in ['ABNORMAL', 'CLOSED', 'RECOVERED']
        assert len(alerts[0]['receivers']) == 2


class TestAlarmStrategiesView:
    @mock.patch("paasng.infras.bkmonitorv3.client.BkMonitorClient", new=StubBKMonitorClient)
    def test_list_alarm_strategies(self, api_client, bk_app):
        resp = api_client.post(
            f'/api/monitor/applications/{bk_app.code}/alarm_strategies/',
        )
        alarm_strategies = resp.data['alarm_strategies']
        assert len(alarm_strategies) == 3
        assert alarm_strategies[0]['is_enabled'] in [True, False]
