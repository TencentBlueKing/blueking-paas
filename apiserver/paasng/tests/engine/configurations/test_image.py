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
from unittest import mock

import pytest

from paas_wl.cnative.specs.crd.bk_app import ApiVersion, BkAppResource
from paas_wl.platform.applications.models import Build
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.configurations.image import (
    RuntimeImageInfo,
    generate_image_repository,
    get_image_repository_template,
    update_image_runtime_config,
)
from paasng.engine.constants import RuntimeType
from paasng.platform.modules.constants import SourceOrigin

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def version():
    return VersionInfo(revision='foo', version_type='tag', version_name='foo')


class TestRuntimeInfo:
    def test_legacy_custom_image(self, bk_module_full, version):
        bk_module_full.source_origin = SourceOrigin.IMAGE_REGISTRY
        bk_module_full.save()
        runtime_info = RuntimeImageInfo(bk_module_full.get_envs("prod").get_engine_app())
        with mock.patch.object(runtime_info.module, "get_source_obj") as m:
            m().get_repo_url.return_value = "docker.io/library/python"

            assert runtime_info.generate_image(version_info=version) == "docker.io/library/python:foo"

    @pytest.mark.parametrize(
        "is_cnb_runtime, expected", [(True, f"{get_image_repository_template()}:{{tag}}"), (False, "")]
    )
    def test_buildpack_runtime(self, bk_module_full, version, is_cnb_runtime, expected):
        bk_module_full.source_origin = SourceOrigin.AUTHORIZED_VCS
        bk_module_full.save()
        bk_module_full.build_config.build_method = RuntimeType.BUILDPACK
        bk_module_full.build_config.save()
        runtime_info = RuntimeImageInfo(bk_module_full.get_envs("prod").get_engine_app())
        with mock.patch("paasng.engine.configurations.image.ModuleRuntimeManager.is_cnb_runtime", new=is_cnb_runtime):
            assert runtime_info.generate_image(
                version_info=version, special_tag=version.version_name
            ) == expected.format(
                app_code=bk_module_full.application.code, module_name=bk_module_full.name, tag=version.version_name
            )

    def test_dockerfile_runtime(self, bk_module_full, version):
        bk_module_full.source_origin = SourceOrigin.AUTHORIZED_VCS
        bk_module_full.save()
        bk_module_full.build_config.build_method = RuntimeType.DOCKERFILE
        bk_module_full.build_config.save()
        runtime_info = RuntimeImageInfo(bk_module_full.get_envs("prod").get_engine_app())
        assert (
            runtime_info.generate_image(version_info=version, special_tag=version.version_name)
            == f"{generate_image_repository(bk_module_full)}:{version.version_name}"
        )

    @pytest.mark.parametrize(
        "bkapp, expected",
        [
            (BkAppResource(apiVersion=ApiVersion.V1ALPHA1, metadata={"name": "foo"}, spec={}), ""),
            (
                BkAppResource(
                    apiVersion=ApiVersion.V1ALPHA2,
                    metadata={"name": "foo"},
                    spec={"build": {"image": "docker.io/library/python"}},
                ),
                "docker.io/library/python:{tag}",
            ),
        ],
    )
    def test_cnative(self, bk_cnative_app, version, bkapp, expected):
        bk_module = bk_cnative_app.get_default_module()
        bk_module.source_origin = SourceOrigin.CNATIVE_IMAGE
        bk_module.save()
        runtime_info = RuntimeImageInfo(bk_module.get_envs("prod").get_engine_app())
        with mock.patch("paasng.engine.configurations.image.get_bkapp", return_value=bkapp):
            assert runtime_info.generate_image(version_info=version) == expected.format(tag=version.version_name)

    @pytest.mark.parametrize(
        "source_origin, expected",
        [(SourceOrigin.IMAGE_REGISTRY, "custom_image"), (SourceOrigin.AUTHORIZED_VCS, "buildpack")],
    )
    def test_type(self, bk_module_full, version, source_origin, expected):
        bk_module_full.source_origin = source_origin.value
        bk_module_full.save()
        runtime_info = RuntimeImageInfo(bk_module_full.get_envs("prod").get_engine_app())

        assert runtime_info.type == expected


class TestUpdateImageRuntimeConfig:
    def test_normal(self, bk_user, bk_module, bk_deployment, with_wl_apps, bk_prod_env):
        build_params = {
            "owner": bk_user,
            "app": bk_prod_env.get_engine_app().to_wl_obj(),
            "image": "nginx:latest",
            "source_type": "foo",
            "branch": "bar",
            "revision": "1",
            "procfile": {"web": "legacycommand manage.py runserver", "worker": "python manage.py celery"},
        }
        wl_build = Build.objects.create(**build_params)
        bk_deployment.update_fields(build_id=wl_build.pk)
        update_image_runtime_config(bk_deployment)
