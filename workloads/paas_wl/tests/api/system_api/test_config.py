# -*- coding: utf-8 -*-
import json

import pytest

from paas_wl.platform.applications.models.config import Config
from paas_wl.platform.system_api.serializers import ConfigSerializer

pytestmark = pytest.mark.django_db


class TestConfigViewSet:
    @pytest.fixture
    def config_url(self, fake_app):
        return f"/regions/{fake_app.region}/apps/{fake_app.name}/config/"

    def test_retrieve(self, api_client, fake_app, config_url):
        response = api_client.get(config_url)
        assert response.status_code == 200
        cfg = Config.objects.filter(app=fake_app).latest()
        assert response.json() == json.loads(response.accepted_renderer.render(ConfigSerializer(cfg).data))

    def test_retrieve_fail(self, api_client, fake_app):
        response = api_client.get(f'/regions/{fake_app.region}/apps/name-not-found/config/')
        assert response.status_code == 404

    def test_update_config(self, api_client, fake_app, config_url):
        data = {"resource_requirements": {"test": "test"}}
        response = api_client.post(config_url, data=data)
        cfg = Config.objects.filter(app=fake_app).latest()
        assert response.status_code == 201
        assert response.json() == json.loads(response.accepted_renderer.render(ConfigSerializer(cfg).data))

    def test_update_config_404(self, api_client, fake_app):
        response = api_client.post(f'/regions/{fake_app.region}/apps/name-not-found/config/', data={})
        assert response.status_code == 404

    def test_update_image(self, api_client, fake_app, config_url):
        response = api_client.post(config_url, data={"image": "xxxxx"})
        assert response.status_code == 201
        assert Config.objects.filter(app=fake_app).latest().get_image() == "xxxxx"
