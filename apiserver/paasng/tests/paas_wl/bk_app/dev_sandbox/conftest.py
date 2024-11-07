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

import pytest

from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.controller import _DevWlAppCreator
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Resources, ResourceSpec, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.kres_entities import (
    CodeEditor,
    CodeEditorService,
    DevSandbox,
    DevSandboxIngress,
    DevSandboxService,
)
from paas_wl.infras.cluster.models import Cluster
from tests.conftest import CLUSTER_NAME_FOR_TESTING


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
def dev_sandbox_code():
    return "devsandbox"


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
def user_dev_wl_app(bk_app, module_name, dev_sandbox_code):
    return _DevWlAppCreator(bk_app, module_name, dev_sandbox_code).create()


@pytest.fixture()
def source_configured_dev_sandbox_entity(user_dev_wl_app, dev_runtime):
    source_code_config = SourceCodeConfig(
        pvc_claim_name="test-pvc",
        workspace="/cnb/devsandbox/src",
        source_fetch_url="http://example.com",
        source_fetch_method=SourceCodeFetchMethod.BK_REPO,
    )
    dev_sandbox_entity = DevSandbox.create(
        user_dev_wl_app,
        dev_runtime,
        resources=Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        ),
        source_code_config=source_code_config,
    )
    dev_sandbox_entity.construct_envs()
    return dev_sandbox_entity


@pytest.fixture()
def code_editor_entity(user_dev_wl_app, dev_runtime):
    config = CodeEditorConfig(
        pvc_claim_name="test-pvc",
        start_dir="/home/coder/project",
        password="test-password",
    )
    code_editor_entity = CodeEditor.create(
        user_dev_wl_app,
        dev_runtime,
        config=config,
        resources=Resources(
            limits=ResourceSpec(cpu="4", memory="2Gi"),
            requests=ResourceSpec(cpu="200m", memory="512Mi"),
        ),
    )
    code_editor_entity.construct_envs()
    return code_editor_entity


@pytest.fixture()
def dev_sandbox_service_entity(dev_wl_app):
    return DevSandboxService.create(dev_wl_app)


@pytest.fixture()
def code_editor_service_entity(dev_wl_app):
    return CodeEditorService.create(dev_wl_app)


@pytest.fixture()
def dev_sandbox_ingress_entity(bk_app, dev_wl_app, module_name):
    return DevSandboxIngress.create(dev_wl_app, bk_app.code)


@pytest.fixture()
def dev_sandbox_ingress_entity_with_dev_sandbox_code(bk_app, dev_wl_app, module_name, dev_sandbox_code):
    return DevSandboxIngress.create(dev_wl_app, bk_app.code, dev_sandbox_code)
