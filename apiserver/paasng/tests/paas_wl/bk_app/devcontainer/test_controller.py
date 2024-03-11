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
from kubernetes.client.apis import VersionApi

from paas_wl.bk_app.devcontainer.controller import DevContainerController
from paas_wl.bk_app.devcontainer.exceptions import DevContainerAlreadyExists
from paas_wl.bk_app.devcontainer.kres_entities.ingress import get_ingress_name, get_sub_domain_host
from paas_wl.bk_app.devcontainer.kres_entities.service import get_service_name
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from tests.conftest import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(scope="session", autouse=True)
def _skip_if_low_k8s_version():
    k8s_client = get_client_by_cluster_name(CLUSTER_NAME_FOR_TESTING)
    k8s_version = VersionApi(k8s_client).get_code()
    if (int(k8s_version.major), int(k8s_version.minor)) < (1, 20):
        pytest.skip("Skip TestDevContainerController because current k8s version less than 1.20")


class TestDevContainerController:
    @pytest.fixture()
    def controller(self, bk_app, module_name, dev_wl_app):
        ctrl = DevContainerController(bk_app, module_name, dev_wl_app)
        yield ctrl
        # just test delete ok!
        ctrl.delete()

    @pytest.fixture()
    def _do_deploy(self, controller):
        envs = {"FOO": "test"}
        controller.deploy(envs=envs)

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_success(self, controller, bk_app, module_name, dev_wl_app):
        container_entity_in_cluster = controller.container_mgr.get(dev_wl_app, dev_wl_app.scheduler_safe_name)
        assert container_entity_in_cluster.runtime.envs == {"FOO": "test"}
        assert container_entity_in_cluster.status.replicas == 1
        assert container_entity_in_cluster.status.ready_replicas in [0, 1]
        assert container_entity_in_cluster.status.to_health_phase() in ["Progressing", "Healthy"]

        service_entity_in_cluster = controller.service_mgr.get(dev_wl_app, get_service_name(dev_wl_app))
        assert service_entity_in_cluster.name == get_service_name(dev_wl_app)

        ingress_entity_in_cluster = controller.ingress_mgr.get(dev_wl_app, get_ingress_name(dev_wl_app))
        assert ingress_entity_in_cluster.name == get_ingress_name(dev_wl_app)
        assert ingress_entity_in_cluster.domains[0].host == get_sub_domain_host(bk_app.code, dev_wl_app, module_name)

    @pytest.mark.usefixtures("_do_deploy")
    def test_deploy_when_already_exists(self, controller, bk_app, module_name, dev_wl_app):
        with pytest.raises(DevContainerAlreadyExists):
            controller.deploy(envs={})

    @pytest.mark.usefixtures("_do_deploy")
    def test_get_container_detail(self, controller, bk_app, module_name, dev_wl_app):
        detail = controller.get_container_detail()
        assert detail.status in ["Progressing", "Healthy"]
        assert detail.url == get_sub_domain_host(bk_app.code, dev_wl_app, module_name)
        assert detail.envs == {"FOO": "test"}
