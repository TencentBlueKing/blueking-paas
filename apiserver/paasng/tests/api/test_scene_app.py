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
import string

import pytest
from django.conf import settings
from django.urls import reverse

from paasng.dev_resources.templates.constants import TemplateType
from paasng.platform.modules.constants import SourceOrigin
from tests.utils import mock
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestSceneApp:
    @pytest.fixture(autouse=True)
    def init_scene_tmpls(self):
        from tests.utils.helpers import create_scene_tmpls

        create_scene_tmpls()

    @pytest.mark.parametrize(
        'query_params, result_count',
        [
            ({'region': settings.DEFAULT_REGION_NAME}, 3),
            ({'region': 'for_test'}, 0),
        ],
    )
    def test_list(self, api_client, query_params, result_count):
        url = reverse('api.templates.list_tmpls', kwargs=dict(tpl_type=TemplateType.SCENE.value))
        response = api_client.get(url, data=query_params)
        assert len(response.data) >= result_count

    @pytest.fixture
    def mock_create_scene_app(self):
        with mock.patch(
            'paasng.platform.applications.views.SourceOrigin.get_default_origins',
            new=lambda *args, **kwargs: [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.IMAGE_REGISTRY, SourceOrigin.SCENE],
        ), mock.patch('paasng.extensions.declarative.application.controller.initialize_smart_module'), mock.patch(
            'paasng.extensions.scene_app.initializer.get_oauth2_client_secret',
            new=lambda *args, **kwargs: 'test_app_secret',
        ):
            yield

    def test_create(self, api_client, mock_create_scene_app):
        url = reverse('api.applications.create_v2')
        app_code = generate_random_string(8, string.ascii_lowercase)
        app_name = generate_random_string(8)
        data = {
            'type': 'default',
            'region': settings.DEFAULT_REGION_NAME,
            'code': app_code,
            'name': app_name,
            'engine_enabled': True,
            'engine_params': {
                'source_init_template': 'scene_tmpl1',
                'source_control_type': 'dft_gitlab',
                'source_repo_url': 'http://example.com/default/git.git',
                'source_origin': SourceOrigin.SCENE.value,
                'source_dir': '',
            },
            'market_params': {'source_url_type': 2, 'enabled': True},
        }
        response = api_client.post(url, data=data)
        assert response.data['application']['code'] == app_code
        assert response.data['application']['is_scene_app'] is True
        assert response.data['source_init_result']
