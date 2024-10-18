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
import uuid
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.models import Build
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.entities import DeployHandleResult
from paasng.platform.engine.deploy.image_release import ImageReleaseMgr
from paasng.platform.engine.handlers import attach_all_phases
from paasng.platform.engine.models.deployment import Deployment, ProcessTmpl

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestHandleProcessesAndDummyBuild:
    @pytest.fixture()
    def deployment_with_build_options(self, bk_stag_env):
        fake_build_id = uuid.uuid4()
        # 创建上一次 deployment
        G(
            Deployment,
            build_id=fake_build_id,
            app_environment=bk_stag_env,
            processes={"web": ProcessTmpl(name="web", command="run server")},
        )
        deployment = G(
            Deployment,
            app_environment=bk_stag_env,
            build_id=fake_build_id,
            advanced_options={"build_id": fake_build_id},
        )
        attach_all_phases(sender=deployment.app_environment, deployment=deployment)
        return deployment

    @pytest.fixture()
    def simple_deployment(self, bk_stag_env):
        deployment = G(Deployment, app_environment=bk_stag_env)
        attach_all_phases(sender=deployment.app_environment, deployment=deployment)
        return deployment

    def test_for_last_build(self, deployment_with_build_options):
        """test ImageReleaseMgr._handle_processes_by_build"""
        deployment = deployment_with_build_options

        ImageReleaseMgr.from_deployment_id(deployment.id)._handle_app_processes_and_dummy_build()
        deployment = Deployment.objects.get(id=deployment.id)
        assert deployment.processes == {"web": ProcessTmpl(name="web", command="run server")}
        assert str(deployment.build_id) == deployment.advanced_options.build_id

    @pytest.mark.usefixtures("_with_wl_apps")
    def test_for_smart_app(self, bk_app, simple_deployment):
        """test ImageReleaseMgr._handle_smart_app_description"""
        app = Application.objects.get(id=bk_app.id)
        app.is_smart_app = True
        app.save()

        with mock.patch(
            "paasng.platform.engine.deploy.image_release.ImageReleaseMgr._handle_smart_app_description",
            return_value=DeployHandleResult(spec_version=AppSpecVersion.VER_3),
        ):
            ImageReleaseMgr.from_deployment_id(simple_deployment.id)._handle_app_processes_and_dummy_build()
            deployment = Deployment.objects.get(id=simple_deployment.id)
            build = Build.objects.get(uuid=deployment.build_id)
            assert build.artifact_metadata.get("use_cnb") is True

    @pytest.mark.usefixtures("_with_wl_apps")
    def test_for_image_app(self, bk_module, simple_deployment):
        """test ImageReleaseMgr._handle_image_app_processes"""
        G(ModuleProcessSpec, module=bk_module, name="web", command=["npm"], args=["run", "server"])

        ImageReleaseMgr.from_deployment_id(simple_deployment.id)._handle_app_processes_and_dummy_build()
        deployment = Deployment.objects.get(id=simple_deployment.id)
        assert deployment.processes["web"].command == "npm run server"
        assert Build.objects.filter(uuid=deployment.build_id).exists()
