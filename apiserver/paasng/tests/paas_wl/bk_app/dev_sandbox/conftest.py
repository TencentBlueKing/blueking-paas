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

from paas_wl.bk_app.dev_sandbox.controller import _DevWlAppCreator
from paas_wl.bk_app.dev_sandbox.entities import Resources, ResourceSpec, Runtime
from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox, DevSandboxIngress, DevSandboxService
from paas_wl.infras.cluster.models import Cluster
from tests.conftest import CLUSTER_NAME_FOR_TESTING


@pytest.fixture(autouse=True)
def _set_default_cluster(settings):
    settings.CLOUD_NATIVE_APP_DEFAULT_CLUSTER = CLUSTER_NAME_FOR_TESTING


@pytest.fixture()
def default_dev_sandbox_cluster():
    return Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)


@pytest.fixture()
def dev_runtime():
    fake_dev_image = "busybox:latest"
    return Runtime(envs={"FOO": "test"}, image=fake_dev_image)


@pytest.fixture()
def module_name():
    return "default"


@pytest.fixture()
def dev_wl_app(bk_app, module_name):
    return _DevWlAppCreator(bk_app, module_name).create()


@pytest.fixture()
def dev_sandbox_entity(dev_wl_app, dev_runtime):
    return DevSandbox.create(
        dev_wl_app,
        dev_runtime,
        resources=Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        ),
    )


@pytest.fixture()
def dev_sandbox_service_entity(dev_wl_app):
    return DevSandboxService.create(dev_wl_app)


@pytest.fixture()
def dev_sandbox_ingress_entity(bk_app, dev_wl_app, module_name):
    return DevSandboxIngress.create(dev_wl_app, bk_app.code)
