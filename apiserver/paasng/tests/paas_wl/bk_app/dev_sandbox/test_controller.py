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

from pathlib import Path
from unittest import mock

import pytest
from kubernetes.client.apis import VersionApi

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController, DevSandboxWithCodeEditorController
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists
from paas_wl.bk_app.dev_sandbox.kres_entities import get_ingress_name, get_service_name, get_sub_domain_host
from paas_wl.bk_app.dev_sandbox.kres_entities.code_editor import get_code_editor_name
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paasng.platform.sourcectl.models import VersionInfo
from tests.conftest import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version():
    k8s_client = get_client_by_cluster_name(CLUSTER_NAME_FOR_TESTING)
    k8s_version = VersionApi(k8s_client).get_code()
    if (int(k8s_version.major), int(k8s_version.minor)) < (1, 20):
        pytest.skip("Skip TestDevContainerController because current k8s version less than 1.20")


class TestDevSandboxController:
    @pytest.fixture()
    def controller(self, bk_app, module_name):
        ctrl = DevSandboxController(bk_app, module_name)
        yield ctrl
        # just test delete ok!
        ctrl.delete()

    @pytest.fixture()
    def _do_deploy(self, controller):
        envs = {"FOO": "test"}
        controller.deploy(envs=envs)

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_success(self, controller, bk_app, module_name, dev_wl_app):
        sandbox_entity_in_cluster = controller.sandbox_mgr.get(dev_wl_app, dev_wl_app.scheduler_safe_name)
        assert sandbox_entity_in_cluster.runtime.envs == {"FOO": "test"}
        assert sandbox_entity_in_cluster.status.replicas == 1
        assert sandbox_entity_in_cluster.status.ready_replicas in [0, 1]
        assert sandbox_entity_in_cluster.status.to_health_phase() in ["Progressing", "Healthy"]

        service_entity_in_cluster = controller.service_mgr.get(dev_wl_app, get_service_name(dev_wl_app))
        assert service_entity_in_cluster.name == get_service_name(dev_wl_app)

        ingress_entity_in_cluster = controller.ingress_mgr.get(dev_wl_app, get_ingress_name(dev_wl_app))
        assert ingress_entity_in_cluster.name == get_ingress_name(dev_wl_app)
        assert ingress_entity_in_cluster.domains[0].host == get_sub_domain_host(bk_app.code, dev_wl_app, module_name)

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_when_already_exists(self, controller, bk_app, module_name, dev_wl_app):
        with pytest.raises(DevSandboxAlreadyExists):
            controller.deploy(envs={})

    @pytest.mark.usefixtures("_do_deploy")
    def test_get_sandbox_detail(self, controller, bk_app, module_name, dev_wl_app):
        detail = controller.get_sandbox_detail()
        assert detail.status in ["Progressing", "Healthy"]
        assert detail.url == get_sub_domain_host(bk_app.code, dev_wl_app, module_name)
        assert detail.envs == {"FOO": "test"}


class TestDevSandboxWithCodeEditorController:
    @pytest.fixture()
    def controller(self, bk_app, module_name, bk_user):
        ctrl = DevSandboxWithCodeEditorController(bk_app, module_name, bk_user)
        yield ctrl
        # just test delete ok!
        ctrl.delete()

    @pytest.fixture()
    def _do_deploy(self, controller):
        dev_sandbox_env_vars = {"FOO": "test"}
        version_info = VersionInfo("1", "v1", "branches")
        relative_source_dir = Path(".")
        password = "123456"
        with mock.patch(
            "paas_wl.bk_app.dev_sandbox.controller.DevSandboxWithCodeEditorController._upload_source_code",
            return_value="example.com",
        ):
            controller.deploy(
                dev_sandbox_env_vars=dev_sandbox_env_vars,
                code_editor_env_vars={},
                version_info=version_info,
                relative_source_dir=relative_source_dir,
                password=password,
            )

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_success(self, controller, bk_app, module_name, user_dev_wl_app):
        sandbox_entity_in_cluster = controller.sandbox_mgr.get(user_dev_wl_app, user_dev_wl_app.scheduler_safe_name)
        assert sandbox_entity_in_cluster.runtime.envs == {
            "FOO": "test",
            "SOURCE_FETCH_METHOD": "BK_REPO",
            "SOURCE_FETCH_URL": "example.com",
            "WORKSPACE": "/cnb/devsandbox/src",
        }
        assert sandbox_entity_in_cluster.status.replicas == 1
        assert sandbox_entity_in_cluster.status.ready_replicas in [0, 1]
        assert sandbox_entity_in_cluster.status.to_health_phase() in ["Progressing", "Healthy"]

        code_editor_entity_in_cluster = controller.code_editor_mgr.get(
            user_dev_wl_app, get_code_editor_name(user_dev_wl_app)
        )
        assert code_editor_entity_in_cluster.runtime.envs == {"PASSWORD": "123456", "START_DIR": "/home/coder/project"}
        assert code_editor_entity_in_cluster.status.replicas == 1
        assert code_editor_entity_in_cluster.status.ready_replicas in [0, 1]
        assert code_editor_entity_in_cluster.status.to_health_phase() in ["Progressing", "Healthy"]

        service_entity_in_cluster = controller.service_mgr.get(user_dev_wl_app, get_service_name(user_dev_wl_app))
        assert service_entity_in_cluster.name == get_service_name(user_dev_wl_app)

        ingress_entity_in_cluster = controller.ingress_mgr.get(user_dev_wl_app, get_ingress_name(user_dev_wl_app))
        assert ingress_entity_in_cluster.name == get_ingress_name(user_dev_wl_app)
        assert ingress_entity_in_cluster.domains[0].host == get_sub_domain_host(
            bk_app.code, user_dev_wl_app, module_name
        )

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_when_already_exists(self, controller, bk_app, module_name, user_dev_wl_app):
        dev_sandbox_env_vars = {"FOO": "test"}
        version_info = VersionInfo("1", "v1", "branches")
        relative_source_dir = Path(".")
        password = "123456"
        with pytest.raises(DevSandboxAlreadyExists), mock.patch(
            "paas_wl.bk_app.dev_sandbox.controller.DevSandboxWithCodeEditorController._upload_source_code",
            return_value="example.com",
        ):
            controller.deploy(
                dev_sandbox_env_vars=dev_sandbox_env_vars,
                code_editor_env_vars={},
                version_info=version_info,
                relative_source_dir=relative_source_dir,
                password=password,
            )

    @pytest.mark.usefixtures("_do_deploy")
    def test_get_sandbox_detail(self, controller, bk_app, module_name, user_dev_wl_app):
        detail = controller.get_detail()
        base_url = get_sub_domain_host(bk_app.code, user_dev_wl_app, module_name)
        username = controller.owner.username

        assert detail.urls.app_url == f"{base_url}/user/{username}/app/"
        assert detail.urls.devserver == f"{base_url}/user/{username}/devserver/"
        assert detail.urls.code_editor_url == f"{base_url}/user/{username}/code_editor/"
        assert detail.dev_sandbox_env_vars == {
            "FOO": "test",
            "SOURCE_FETCH_METHOD": "BK_REPO",
            "SOURCE_FETCH_URL": "example.com",
            "WORKSPACE": "/cnb/devsandbox/src",
        }
        assert detail.code_editor_env_vars == {"PASSWORD": "123456", "START_DIR": "/home/coder/project"}
        assert detail.dev_sandbox_status in ["Progressing", "Healthy"]
        assert detail.code_editor_status in ["Progressing", "Healthy"]
