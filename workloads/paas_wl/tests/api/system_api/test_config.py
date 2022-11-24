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
