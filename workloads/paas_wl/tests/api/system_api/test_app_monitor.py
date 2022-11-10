# -*- coding: utf-8 -*-
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
