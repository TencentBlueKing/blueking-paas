# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import tempfile
from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paasng.infras.oauth2.utils import create_oauth2_client
from paasng.platform.applications.models import Application, ApplicationEnvironment
from paasng.platform.applications.utils import create_default_module
from paasng.platform.engine.models import EngineApp
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.manager import ModuleInitializer
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner, Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.templates.models import Template
from tests.utils.helpers import register_iam_after_create_application

pytestmark = [pytest.mark.django_db, pytest.mark.xdist_group(name="legacy-db")]


@pytest.fixture()
def raw_module(bk_user) -> Module:
    """Raw application and module objects without initializing"""
    application = G(
        Application, owner=bk_user.pk, code="awesome-app", language="Python", region=settings.DEFAULT_REGION_NAME
    )
    register_iam_after_create_application(application)
    module = create_default_module(application)
    create_oauth2_client(application.code, application.region)
    return module


class TestModuleInitializer:
    def test_create_engine_apps(self, raw_module, mock_wl_services_in_creation):
        app_initializer = ModuleInitializer(raw_module)
        app_initializer.create_engine_apps()

        assert EngineApp.objects.count() == 2
        assert ApplicationEnvironment.objects.count() == 2
        assert raw_module.envs.get(environment="stag").get_engine_app() is not None

    @pytest.mark.parametrize(
        ("services_in_template", "is_default", "expected_bind_service_cnt"),
        [
            ({}, True, 0),
            ({"mysql": {"specs": {}}}, True, 1),
            ({"mysql": {"specs": {}}}, False, 1),
        ],
    )
    def test_bind_default_services(
        self, services_in_template, is_default, expected_bind_service_cnt, settings, raw_module
    ):
        raw_module.source_init_template = "dj18_with_auth"
        raw_module.is_default = is_default
        raw_module.save()

        module_initializer = ModuleInitializer(raw_module)
        with mock.patch("paasng.platform.templates.manager.Template.objects.get") as mocked_get_tmpl, mock.patch(
            "paasng.platform.modules.manager.mixed_service_mgr"
        ) as mocked_service_mgr:
            mocked_get_tmpl.return_value = Template(
                name="foo",
                language="Python",
                # Set preset services
                preset_services_config=services_in_template,
                enabled_regions=[settings.DEFAULT_REGION_NAME],
            )

            module_initializer.bind_default_services()

            if expected_bind_service_cnt:
                assert mocked_service_mgr.find_by_name.called
            assert mocked_service_mgr.bind_service.call_count == expected_bind_service_cnt

    def test_bind_default_runtime(self, raw_module, settings):
        raw_module.source_init_template = "test_template"
        raw_module.save()
        application = raw_module.application

        # Initialize builder/runner/buildpacks
        slugbuilder = G(AppSlugBuilder, name="test", is_hidden=False, region=application.region)
        default_buildpack = G(
            AppBuildPack,
            name="default",
            language=application.language,
            is_hidden=False,
            region=application.region,
        )
        slugbuilder.buildpacks.add(default_buildpack)

        buildpack = G(
            AppBuildPack,
            name="test",
            language="invalid_language",
            is_hidden=False,
            region=application.region,
        )
        slugbuilder.buildpacks.add(buildpack)
        G(AppSlugRunner, name="test", is_hidden=False, region=application.region)

        # Override settings
        settings.DEFAULT_RUNTIME_IMAGES = {application.region: slugbuilder.name}

        with mock.patch("paasng.platform.modules.manager.Template.objects.get") as mocked_get_tmpl:
            mocked_get_tmpl.return_value = Template(
                name="bar",
                language="Python",
                required_buildpacks=[buildpack.name],
                enabled_regions=[settings.DEFAULT_REGION_NAME],
            )
            module_initializer = ModuleInitializer(raw_module)
            module_initializer.bind_default_runtime()

            manager = ModuleRuntimeManager(raw_module)
            buildpacks = manager.list_buildpacks()

            assert len(buildpacks) == 2
            assert buildpacks[0].name == buildpack.name
            assert buildpacks[1].name == default_buildpack.name
            assert buildpacks[1].language == raw_module.language

    @pytest.mark.usefixtures("_init_tmpls")
    def test_initialize_vcs(self, raw_module):
        with mock.patch("paasng.platform.sourcectl.svn.client.RepoProvider") as mocked_provider, mock.patch(
            "paasng.platform.sourcectl.connector.SvnRepositoryClient"
        ) as mocked_client, mock.patch(
            "paasng.platform.templates.templater.Templater.download_tmpl"
        ) as mocked_download:
            mocked_provider().provision.return_value = {"repo_url": "mocked_repo_url"}
            mocked_download.return_value = Path(tempfile.mkdtemp())

            raw_module.source_init_template = settings.DUMMY_TEMPLATE_NAME
            raw_module.source_origin = SourceOrigin.AUTHORIZED_VCS
            raw_module.save()

            result = ModuleInitializer(raw_module).initialize_vcs_with_template("dft_bk_svn")

            mocked_client.assert_called()
            mocked_client().sync_dir.assert_called()
            assert result["code"] == "OK"
            assert result["dest_type"] == "svn"
            assert "extra_info" in result

    @pytest.mark.parametrize(
        ("source_origin"),
        [
            (SourceOrigin.BK_LESS_CODE),
            (SourceOrigin.AI_AGENT),
        ],
    )
    @pytest.mark.usefixtures("_init_tmpls")
    def test_external_package(self, raw_module, source_origin):
        raw_module.source_init_template = settings.DUMMY_TEMPLATE_NAME
        raw_module.source_origin = source_origin
        raw_module.save()

        assert ModuleInitializer(raw_module)._should_initialize_vcs() is False
        assert ModuleSpecs(raw_module).has_template_code is False
