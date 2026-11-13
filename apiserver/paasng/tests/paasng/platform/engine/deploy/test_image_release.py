# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from paas_wl.bk_app.cnative.specs.models import AppModelRevision
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, SMartAppExtraInfo
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.entities import DeployHandleResult
from paasng.platform.engine.deploy.image_release import ImageReleaseMgr
from paasng.platform.engine.exceptions import DeployShouldAbortError
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
    @pytest.mark.parametrize(
        ("current_procs", "built_procs", "has_build_revision", "expected_missing"),
        [
            (["web", "def-w"], ["web", "celery"], True, "def-w"),
            (["web"], ["web", "celery"], True, None),
            (["web", "def-w"], ["web"], False, None),
        ],
    )
    def test_cnative_procs_check(
        self,
        bk_module,
        bk_stag_env,
        deployment_with_build_options,
        current_procs,
        built_procs,
        has_build_revision,
        expected_missing,
    ):
        """选已构建镜像部署云原生应用时，当前进程必须都在镜像构建时的进程里"""
        application = bk_module.application
        application.type = ApplicationType.CLOUD_NATIVE
        application.save(update_fields=["type"])

        deployment = deployment_with_build_options
        build_id = deployment.advanced_options["build_id"]
        Build.objects.create(
            uuid=build_id,
            app=bk_stag_env.wl_app,
            module_id=bk_module.id,
            bkapp_revision_id=self._create_revision(bk_module, built_procs) if has_build_revision else None,
            tenant_id=bk_module.tenant_id,
        )
        deployment.update_fields(bkapp_revision_id=self._create_revision(bk_module, current_procs))

        mgr = ImageReleaseMgr.from_deployment_id(deployment.id)
        if expected_missing:
            with pytest.raises(DeployShouldAbortError, match=expected_missing):
                mgr._handle_app_processes_and_dummy_build()
        else:
            mgr._handle_app_processes_and_dummy_build()
            assert Deployment.objects.get(id=deployment.id).processes

    @staticmethod
    def _create_revision(module, proc_names: list[str]) -> int:
        json_value = {"spec": {"processes": [{"name": name} for name in proc_names]}}
        return AppModelRevision.objects.create(
            application_id=module.application.id,
            module_id=module.id,
            version="paas.bk.tencent.com/v1alpha2",
            json_value=json_value,
            yaml_value="",
            tenant_id=module.tenant_id,
        ).id

    @pytest.mark.usefixtures("_with_wl_apps")
    @pytest.mark.parametrize(
        "init_artifact_metadata",
        [
            {},
            {"use_cnb": True},
            {"use_cnb": False},
            {"use_cnb": True, "proc_entrypoints": {"web": ["frontend-web"]}},
            {"use_cnb": False, "proc_entrypoints": {"web": ["web"]}},
        ],
    )
    def test_for_smart_app(self, bk_app, bk_module, simple_deployment, init_artifact_metadata):
        """test ImageReleaseMgr._handle_smart_app_description"""
        app = Application.objects.get(id=bk_app.id)
        app.is_smart_app = True
        app.save()

        smart_app_extra = SMartAppExtraInfo.objects.create(app=app)
        smart_app_extra.set_use_cnb_flag(bool(init_artifact_metadata.get("use_cnb")))

        proc_entrypoints = init_artifact_metadata.get("proc_entrypoints") or {}
        if proc_entrypoints:
            smart_app_extra.set_proc_entrypoints(bk_module.name, proc_entrypoints)

        with mock.patch(
            "paasng.platform.engine.deploy.image_release.ImageReleaseMgr._handle_smart_app_description",
            return_value=DeployHandleResult(spec_version=AppSpecVersion.VER_3),
        ):
            ImageReleaseMgr.from_deployment_id(simple_deployment.id)._handle_app_processes_and_dummy_build()
            deployment = Deployment.objects.get(id=simple_deployment.id)
            build = Build.objects.get(uuid=deployment.build_id)

            assert build.artifact_metadata.use_cnb == bool(init_artifact_metadata.get("use_cnb"))
            assert build.artifact_metadata.proc_entrypoints == init_artifact_metadata.get("proc_entrypoints")

    @pytest.mark.usefixtures("_with_wl_apps")
    def test_for_image_app(self, bk_module, simple_deployment):
        """test ImageReleaseMgr._handle_image_app_processes"""
        G(ModuleProcessSpec, module=bk_module, name="web", command=["npm"], args=["run", "server"])

        ImageReleaseMgr.from_deployment_id(simple_deployment.id)._handle_app_processes_and_dummy_build()
        deployment = Deployment.objects.get(id=simple_deployment.id)
        assert deployment.processes["web"].command == "npm run server"
        assert Build.objects.filter(uuid=deployment.build_id).exists()
