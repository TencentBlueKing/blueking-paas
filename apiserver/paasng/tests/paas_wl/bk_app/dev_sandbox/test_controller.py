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
from unittest import mock

import pytest
from kubernetes.client.apis import VersionApi

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvKey
from paas_wl.bk_app.dev_sandbox.controller import DevSandboxController
from paas_wl.bk_app.dev_sandbox.exceptions import DevSandboxAlreadyExists
from paas_wl.bk_app.dev_sandbox.names import (
    get_dev_sandbox_ingress_name,
    get_dev_sandbox_name,
    get_dev_sandbox_service_name,
)
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version():
    k8s_client = get_client_by_cluster_name(CLUSTER_NAME_FOR_TESTING)
    k8s_version = VersionApi(k8s_client).get_code()
    if (int(k8s_version.major), int(k8s_version.minor)) < (1, 20):
        pytest.skip("Skip TestDevContainerController because current k8s version less than 1.20")


class TestDevSandboxController:
    @pytest.fixture()
    def controller(self, dev_sandbox_model):
        ctrl = DevSandboxController(dev_sandbox_model)
        yield ctrl

        ctrl.delete()

    @pytest.fixture(autouse=True)
    def _do_deploy(self, controller, dev_sandbox):
        with mock.patch(
            "paas_wl.bk_app.dev_sandbox.controller.ModuleRuntimeManager.get_dev_sandbox_image",
            return_value="bkpaas/bk-dev-heroku-noble:v2.0.0",
        ):
            controller.deploy(
                dev_sandbox.runtime.envs,
                dev_sandbox.source_code_cfg,
                dev_sandbox.code_editor_cfg,
            )

    def test_deploy_success(self, controller, dev_sandbox, dev_wl_app, default_cluster):
        sandbox = controller.sandbox_mgr.get(dev_wl_app, get_dev_sandbox_name(dev_wl_app))
        assert sandbox.runtime.envs == {
            "FOO": "BAR",
            "WORKSPACE": "/data/workspace",
            "TOKEN": sandbox.runtime.envs[DevSandboxEnvKey.TOKEN],
            "SOURCE_FETCH_METHOD": "BK_REPO",
            "SOURCE_FETCH_URL": "http://bkrepo.example.com",
            "ENABLE_CODE_EDITOR": "true",
            "PASSWORD": dev_sandbox.code_editor_cfg.password,
        }

        service = controller.service_mgr.get(dev_wl_app, get_dev_sandbox_service_name(dev_wl_app))
        assert service.name == get_dev_sandbox_service_name(dev_wl_app)

        ingress = controller.ingress_mgr.get(dev_wl_app, get_dev_sandbox_ingress_name(dev_wl_app))
        assert ingress.name == get_dev_sandbox_ingress_name(dev_wl_app)
        assert (
            ingress.domains[0].host
            == f"dev-dot-{dev_wl_app.module_name}-dot-{dev_wl_app.paas_app_code}."
            + default_cluster.ingress_config.default_root_domain.name
        )

    def test_deploy_when_already_exists(self, controller, dev_sandbox):
        with pytest.raises(DevSandboxAlreadyExists):
            controller.deploy(dev_sandbox.runtime.envs, dev_sandbox.source_code_cfg, None)

    def test_get_sandbox_detail(self, controller, dev_sandbox_model, dev_sandbox, default_cluster):
        detail = controller.get_detail()
        assert (
            detail.urls.base
            == f"dev-dot-{dev_sandbox_model.module.name}-dot-"
            + f"{dev_sandbox_model.module.application.code}."
            + default_cluster.ingress_config.default_root_domain.name
            + f"/dev_sandbox/{dev_sandbox.code}"
        )
        assert detail.status in ["pending", "ready"]
        assert all(item in detail.envs.items() for item in dev_sandbox.runtime.envs.items())
