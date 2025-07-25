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

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.bk_app.dev_sandbox.controller import DevWlAppConstructor
from paas_wl.bk_app.dev_sandbox.entities import CodeEditorConfig, Runtime, SourceCodeConfig
from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox, DevSandboxIngress, DevSandboxService
from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.dev_sandbox.models import DevSandbox as DevSandboxModel
from paasng.accessories.dev_sandbox.utils import generate_password
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING


@pytest.fixture()
def default_cluster():
    return Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)


@pytest.fixture()
def dev_sandbox_model(bk_cnative_app, bk_module) -> DevSandboxModel:
    return DevSandboxModel.objects.create(module=bk_module, env_vars={}, version_info=None, owner="admin")


@pytest.fixture()
def dev_wl_app(dev_sandbox_model) -> WlApp:
    return DevWlAppConstructor(dev_sandbox_model).construct()


@pytest.fixture()
def dev_sandbox(dev_wl_app, dev_sandbox_model) -> DevSandbox:
    return DevSandbox.create(
        dev_wl_app,
        dev_sandbox_model.code,
        dev_sandbox_model.token,
        Runtime(
            envs={"FOO": "BAR"},
            image="mirrors.example.com/paasng/dev-sandbox:latest",
        ),
        SourceCodeConfig(
            source_fetch_url="http://bkrepo.example.com",
            source_fetch_method=SourceCodeFetchMethod.BK_REPO,
        ),
        CodeEditorConfig(password=generate_password()),
    )


@pytest.fixture()
def dev_sandbox_service(dev_sandbox) -> DevSandboxService:
    return DevSandboxService.create(dev_sandbox)


@pytest.fixture()
def dev_sandbox_ingress(dev_sandbox) -> DevSandboxIngress:
    return DevSandboxIngress.create(dev_sandbox)
