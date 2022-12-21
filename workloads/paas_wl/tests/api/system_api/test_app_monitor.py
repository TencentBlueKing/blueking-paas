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
import pytest
from django.urls import reverse
from django_dynamic_fixture import G

from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor

pytestmark = pytest.mark.django_db


class TestAppMetricsMonitorViewSet:
    @pytest.fixture
    def url(self, fake_app, settings):
        return reverse(
            "sys_api.app.metrics_monitor", kwargs={"region": settings.FOR_TESTS_DEFAULT_REGION, "name": fake_app.name}
        )

    def test_create(self, api_client, url):
        data = {"port": 5000, "target_port": 5000}
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200

        pk = resp.json()["id"]
        instance = AppMetricsMonitor.objects.get(pk=pk)
        for k, v in data.items():
            assert getattr(instance, k) == v

    def test_update(self, api_client, fake_app, url):
        instance = G(AppMetricsMonitor, app=fake_app, port=80, target_port=80)
        resp = api_client.get(url)

        assert resp.json() == {
            'id': instance.pk,
            'port': 80,
            'target_port': 80,
            'is_enabled': True,
        }

        resp = api_client.post(
            url, data={"path": "/metrics/", "port": 5000, "target_port": 5000, "protocol": "UDP", "username": "foo"}
        )
        assert resp.status_code == 200

        assert resp.json() == {
            'id': instance.pk,
            'port': 5000,
            'target_port': 5000,
            'is_enabled': True,
        }
