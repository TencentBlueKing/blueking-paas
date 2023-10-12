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
from django.conf import settings
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture()
def image_name():
    return generate_random_string()


@pytest.fixture
def py_buildpack():
    buildpack = G(AppBuildPack, name="python", region=settings.DEFAULT_REGION_NAME, language="Python")
    return buildpack


@pytest.fixture
def nodejs_buildpack():
    buildpack = G(AppBuildPack, name="nodejs", region=settings.DEFAULT_REGION_NAME, language="NodeJS")
    return buildpack


@pytest.fixture
def extra_buildpack():
    buildpack = G(AppBuildPack, name="extra", region=settings.DEFAULT_REGION_NAME)
    return buildpack


@pytest.fixture
def slugbuilder(py_buildpack, nodejs_buildpack, extra_buildpack, image_name):
    slugbuilder = G(AppSlugBuilder, name=image_name, region=settings.DEFAULT_REGION_NAME, is_default=True)
    slugbuilder.buildpacks.add(py_buildpack)
    slugbuilder.buildpacks.add(nodejs_buildpack)
    slugbuilder.buildpacks.add(extra_buildpack)
    return slugbuilder


@pytest.fixture
def slugrunner(image_name):
    slugrunner = G(AppSlugRunner, name=image_name, region=settings.DEFAULT_REGION_NAME, is_default=True)
    return slugrunner


@pytest.fixture
def init_tmpls():
    Template.objects.get_or_create(
        name="python",
        defaults={
            'type': TemplateType.NORMAL,
            'display_name_zh_cn': 'Python 开发框架',
            'display_name_en': 'Python Template',
            'description_zh_cn': '...',
            'description_en': '...',
            'language': 'Python',
            'market_ready': True,
            'preset_services_config': {'mysql': {}},
            'blob_url': {settings.DEFAULT_REGION_NAME: f'file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz'},
            'enabled_regions': [settings.DEFAULT_REGION_NAME],
            'required_buildpacks': ["extra"],
            'tags': [],
            'repo_url': 'http://github.com/blueking/dummy_tmpl',
        },
    )

    Template.objects.get_or_create(
        name="nodejs",
        defaults={
            'type': TemplateType.NORMAL,
            'display_name_zh_cn': 'NodeJS 开发框架',
            'display_name_en': 'NodeJS Template',
            'description_zh_cn': '...',
            'description_en': '...',
            'language': 'NodeJS',
            'market_ready': True,
            'preset_services_config': {'mysql': {}},
            'blob_url': {settings.DEFAULT_REGION_NAME: f'file:{settings.BASE_DIR}/tests/contents/dummy-tmpl.tar.gz'},
            'enabled_regions': [settings.DEFAULT_REGION_NAME],
            'required_buildpacks': [],
            'tags': [],
            'repo_url': 'http://github.com/blueking/dummy_tmpl',
        },
    )


class TestRegionTemplateViewSet:
    @pytest.mark.parametrize(
        'region, result_count',
        [
            (settings.DEFAULT_REGION_NAME, 2),
            ("region-not-exist", 0),
        ],
    )
    def test_list(self, init_tmpls, api_client, region, result_count):
        url = reverse('api.templates.list', kwargs=dict(tpl_type=TemplateType.NORMAL.value, region=region))
        response = api_client.get(url)
        assert len(response.data) >= result_count

    @pytest.mark.parametrize(
        "tpl_name, expected_buildpacks",
        [("python", [{"name": "extra"}, {"name": "python"}]), ("nodejs", [{"name": "nodejs"}])],
    )
    def test_retrieve(
        self, request, api_client, init_tmpls, slugbuilder, slugrunner, image_name, tpl_name, expected_buildpacks
    ):
        url = reverse(
            'api.templates.detail',
            kwargs=dict(tpl_type=TemplateType.NORMAL.value, region=settings.DEFAULT_REGION_NAME, tpl_name=tpl_name),
        )
        response = api_client.get(url)
        assert response.status_code == 200

        data = response.json()

        build_config = data["build_config"]
        assert build_config["build_method"] == "buildpack"
        assert build_config["bp_stack_name"] == image_name
        assert "{app_code}" in build_config["image_repository_template"]
        assert "{module_name}" in build_config["image_repository_template"]
        assert [{"name": bp["name"]} for bp in build_config["buildpacks"]] == expected_buildpacks

        slugbuilder = data["slugbuilder"]
        assert slugbuilder["name"] == image_name
