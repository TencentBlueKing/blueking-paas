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
from django_dynamic_fixture import G

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.helpers import ModuleRuntimeBinder, ModuleRuntimeManager
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, BuildConfig
from paasng.platform.modules.models.build_cfg import ImageTagOptions
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


_placeholder_response = {
    "bp_stack_name": None,
    "buildpacks": None,
    "dockerfile_path": None,
    "docker_build_args": None,
    "image_repository": None,
    "image_credential_name": None,
}


class TestModuleBuildConfigViewSet:
    @pytest.fixture(autouse=True)
    def setup_settings(self, settings):
        settings.APP_DOCKER_REGISTRY_HOST = "example.com"
        settings.APP_DOCKER_REGISTRY_NAMESPACE = "bkapps"

    @pytest.fixture
    def bp_stack_name(self):
        return generate_random_string()

    @pytest.fixture
    def buildpack_x(self, settings):
        buildpack = G(AppBuildPack, name="x", region=settings.DEFAULT_REGION_NAME, language="Python")
        return buildpack

    @pytest.fixture
    def buildpack_y(self, settings):
        buildpack = G(AppBuildPack, name="y", region=settings.DEFAULT_REGION_NAME, language="Python")
        return buildpack

    @pytest.fixture
    def buildpack_z(self, settings):
        buildpack = G(AppBuildPack, name="z", region=settings.DEFAULT_REGION_NAME, language="Python")
        return buildpack

    @pytest.fixture
    def slugbuilder(self, settings, buildpack_x, buildpack_y, buildpack_z, bp_stack_name):
        slugbuilder = G(
            AppSlugBuilder,
            name=bp_stack_name,
            region=settings.DEFAULT_REGION_NAME,
            image="example.com/foo",
            tag="bar",
            is_hidden=False,
        )
        slugbuilder.buildpacks.add(buildpack_x)
        slugbuilder.buildpacks.add(buildpack_y)
        slugbuilder.buildpacks.add(buildpack_z)
        return slugbuilder

    @pytest.fixture
    def slugrunner(self, settings, bp_stack_name):
        slugrunner = G(AppSlugRunner, name=bp_stack_name, region=settings.DEFAULT_REGION_NAME, is_hidden=False)
        return slugrunner

    def test_retrieve_legacy_bp(self, api_client, bk_app, bk_module):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.get(url)
        assert resp.json() == {
            **_placeholder_response,
            'image_repository': f'example.com/bkapps/{bk_app.code}/{bk_module.name}',
            'build_method': 'buildpack',
            'tag_options': {'prefix': None, 'with_version': True, 'with_build_time': True, 'with_commit_id': False},
            'bp_stack_name': None,
            'buildpacks': [],
        }

    def test_retrieve_bp(self, api_client, bk_app, bk_module, slugbuilder, slugrunner, buildpack_x):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        binder = ModuleRuntimeBinder(bk_module)
        binder.bind_image(slugrunner, slugbuilder)
        binder.bind_buildpack(buildpack_x)

        resp = api_client.get(url)
        assert resp.json() == {
            **_placeholder_response,
            'image_repository': f'example.com/bkapps/{bk_app.code}/{bk_module.name}',
            'build_method': 'buildpack',
            'tag_options': {'prefix': None, 'with_version': True, 'with_build_time': True, 'with_commit_id': False},
            'bp_stack_name': slugbuilder.name,
            'buildpacks': [
                {
                    'id': buildpack_x.id,
                    'language': buildpack_x.language,
                    'name': buildpack_x.name,
                    'display_name': buildpack_x.display_name,
                    'description': buildpack_x.description,
                }
            ],
        }

    def test_retrieve_docker(self, api_client, bk_app, bk_module):
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = RuntimeType.DOCKERFILE
        cfg.dockerfile_path = "rootfs/Dockerfile"
        cfg.docker_build_args = {"GO_VERSION": "1.19", "GOARCH": "amd64", "CFLAGS": "-g -Wall"}
        cfg.save()
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.get(url)
        assert resp.json() == {
            **_placeholder_response,  # type: ignore
            'image_repository': f'example.com/bkapps/{bk_app.code}/{bk_module.name}',
            'build_method': 'dockerfile',
            'tag_options': {'prefix': None, 'with_version': True, 'with_build_time': True, 'with_commit_id': False},
            'dockerfile_path': 'rootfs/Dockerfile',
            'docker_build_args': {'CFLAGS': '-g -Wall', 'GOARCH': 'amd64', 'GO_VERSION': '1.19'},
        }

    def test_retrieve_custom_image(self, api_client, bk_app, bk_module):
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = RuntimeType.CUSTOM_IMAGE
        cfg.image_repository = "example.com/foo"
        cfg.image_credential_name = "foo"
        cfg.save()
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.get(url)

        assert resp.json() == {
            **_placeholder_response,  # type: ignore
            'image_repository': 'example.com/foo',
            'image_credential_name': 'foo',
            'build_method': 'custom_image',
        }

    def test_modify_bp(
        self,
        api_client,
        bk_app,
        bk_module,
        bp_stack_name,
        slugbuilder,
        slugrunner,
        buildpack_x,
        buildpack_y,
        buildpack_z,
    ):
        data = {
            'build_method': RuntimeType.BUILDPACK,
            'tag_options': {'prefix': "foo", 'with_version': True, 'with_build_time': False, 'with_commit_id': True},
            'bp_stack_name': bp_stack_name,
            'buildpacks': [{"id": buildpack_z.id}, {"id": buildpack_x.id}, {"id": buildpack_y.id}],
        }
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        assert cfg.build_method == RuntimeType.BUILDPACK
        assert cfg.buildpack_builder == slugbuilder
        assert cfg.buildpack_runner == slugrunner
        assert cfg.buildpacks.count() == 3
        assert cfg.tag_options == ImageTagOptions("foo", True, False, True)
        assert ModuleRuntimeManager(bk_module).list_buildpacks() == [buildpack_z, buildpack_x, buildpack_y]

    def test_modify_dockerbuild(self, api_client, bk_app, bk_module):
        data = {
            'build_method': RuntimeType.DOCKERFILE,
            'tag_options': {'prefix': "foo", 'with_version': False, 'with_build_time': False, 'with_commit_id': True},
            'dockerfile_path': "rootfs/Dockerfile",
            'docker_build_args': {"GO_VERSION": "1.19", "GOARCH": "amd64", "CFLAGS": "-g -Wall"},
        }
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        assert cfg.build_method == RuntimeType.DOCKERFILE
        assert cfg.tag_options == ImageTagOptions("foo", False, False, True)
        assert cfg.docker_build_args == {"GO_VERSION": "1.19", "GOARCH": "amd64", "CFLAGS": "-g -Wall"}

    def test_modify_dockerbuild_with_emtpy_build_args(self, api_client, bk_app, bk_module):
        data = {
            'build_method': RuntimeType.DOCKERFILE,
            'tag_options': {'prefix': "foo", 'with_version': False, 'with_build_time': False, 'with_commit_id': True},
            'dockerfile_path': "rootfs/Dockerfile",
            'docker_build_args': {},
        }
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        assert cfg.build_method == RuntimeType.DOCKERFILE
        assert cfg.tag_options == ImageTagOptions("foo", False, False, True)
        assert cfg.docker_build_args == {}

    def test_modify_custom_image(self, api_client, bk_app, bk_module):
        data = {
            'build_method': RuntimeType.CUSTOM_IMAGE,
            'image_repository': 'example.com/bar',
            'image_credential_name': 'bar',
        }
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.post(url, data=data)
        assert resp.status_code == 200
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        assert cfg.build_method == RuntimeType.CUSTOM_IMAGE
        assert cfg.image_repository == "example.com/bar"
        assert cfg.image_credential_name == "bar"

    @pytest.mark.parametrize(
        "data",
        [
            {
                # 传递了错误的构建方式
                'build_method': RuntimeType.BUILDPACK,
                'tag_options': {
                    'prefix': "foo",
                    'with_version': True,
                    'with_build_time': False,
                    'with_commit_id': True,
                },
                'dockerfile_path': "rootfs/Dockerfile",
                'docker_build_args': {"GO_VERSION": "1.19", "GOARCH": "amd64", "CFLAGS": "-g -Wall"},
            },
            {
                'build_method': RuntimeType.DOCKERFILE,
                'tag_options': {
                    # 传递非法的 prefix
                    'prefix': "-foo",
                    'with_version': True,
                    'with_build_time': False,
                    'with_commit_id': True,
                },
                'dockerfile_path': "rootfs/Dockerfile",
                'docker_build_args': {"GO_VERSION": "1.19", "GOARCH": "amd64", "CFLAGS": "-g -Wall"},
            },
            {
                'build_method': RuntimeType.BUILDPACK,
                'tag_options': {
                    'prefix': "foo",
                    'with_version': True,
                    'with_build_time': False,
                    'with_commit_id': True,
                },
                # 传递了不存在的 bp stack
                'bp_stack_name': "unknown-bp",
            },
        ],
    )
    def test_modify_wrong_args(self, api_client, bk_app, bk_module, data):
        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/build_config/"
        resp = api_client.post(url, data=data)
        assert resp.status_code == 400
