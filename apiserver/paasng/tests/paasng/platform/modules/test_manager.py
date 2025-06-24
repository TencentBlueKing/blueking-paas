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
        Application,
        owner=bk_user.pk,
        code="awesome-app",
        language="Python",
        region=settings.DEFAULT_REGION_NAME,
        creator=bk_user,
    )
    register_iam_after_create_application(application)
    module = create_default_module(application)
    create_oauth2_client(application.code, application.app_tenant_mode, application.app_tenant_id)
    return module


class TestModuleInitializer:
    def test_create_engine_apps(self, raw_module, mock_wl_services_in_creation):
        app_initializer = ModuleInitializer(raw_module)
        app_initializer.create_engine_apps()

        assert EngineApp.objects.count() == 2
        assert ApplicationEnvironment.objects.count() == 2
        assert raw_module.envs.get(environment="stag").get_engine_app() is not None

    @pytest.mark.parametrize(
        ("services_in_template", "is_default", "bind_call_cnt"),
        [
            ({}, True, 0),
            ({"mysql": {"specs": {}}}, True, 1),
            ({"mysql": {"specs": {}}}, False, 1),
        ],
    )
    def test_bind_default_services(self, services_in_template, is_default, bind_call_cnt, settings, raw_module):
        raw_module.source_init_template = "dj18_with_auth"
        raw_module.is_default = is_default
        raw_module.save()

        module_initializer = ModuleInitializer(raw_module)
        with (
            mock.patch("paasng.platform.templates.manager.Template.objects.get") as mocked_get_tmpl,
            mock.patch("paasng.platform.modules.manager.mixed_service_mgr") as mocked_service_mgr,
        ):
            mocked_get_tmpl.return_value = Template(
                name="foo",
                language="Python",
                # Set preset services
                preset_services_config=services_in_template,
            )

            module_initializer.bind_default_services()

            if bind_call_cnt:
                assert mocked_service_mgr.find_by_name.called
            assert mocked_service_mgr.bind_service_use_first_plan.call_count == bind_call_cnt

    def test_bind_default_runtime(self, raw_module, settings):
        raw_module.source_init_template = "test_template"
        raw_module.save()
        application = raw_module.application

        # Initialize builder/runner/buildpacks
        slugbuilder = G(AppSlugBuilder, name="test", is_hidden=False)
        default_buildpack = G(
            AppBuildPack,
            name="default",
            language=application.language,
            is_hidden=False,
        )
        slugbuilder.buildpacks.add(default_buildpack)

        buildpack = G(
            AppBuildPack,
            name="test",
            language="invalid_language",
            is_hidden=False,
        )
        slugbuilder.buildpacks.add(buildpack)
        G(AppSlugRunner, name="test", is_hidden=False)

        # Override settings
        settings.DEFAULT_RUNTIME_IMAGES = slugbuilder.name

        with mock.patch("paasng.platform.modules.manager.Template.objects.get") as mocked_get_tmpl:
            mocked_get_tmpl.return_value = Template(
                name="bar",
                language="Python",
                required_buildpacks=[buildpack.name],
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
        with (
            mock.patch("paasng.platform.sourcectl.svn.client.RepoProvider") as mocked_provider,
            mock.patch(
                "paasng.platform.templates.templater.TemplateRenderer.download_from_blob_storage"
            ) as mocked_download,
        ):
            mocked_provider().provision.return_value = {"repo_url": "mocked_repo_url"}
            mocked_download.return_value = Path(tempfile.mkdtemp())

            raw_module.source_init_template = settings.DUMMY_TEMPLATE_NAME
            raw_module.source_origin = SourceOrigin.AUTHORIZED_VCS
            raw_module.save()

            result = ModuleInitializer(raw_module).initialize_vcs_with_template(
                "dft_bk_svn",
                repo_url="http://git.example.com/test-group/repo1.git",
            )
            assert result.code == "OK"
            assert "downloadable_address" in result.extra_info

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
