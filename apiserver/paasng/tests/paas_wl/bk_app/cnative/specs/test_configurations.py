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

from paas_wl.bk_app.cnative.specs.configurations import EnvVarsReader
from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvOverlay, EnvVar, EnvVarOverlay
from paas_wl.bk_app.cnative.specs.models import AppModelResource, create_app_resource
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestEnvVarsReader:
    @pytest.mark.parametrize(
        "envs",
        [
            ([EnvVar(name="foo", value="")]),
            ([EnvVar(name="foo", value="1"), EnvVar(name="bar", value="2")]),
        ],
    )
    def test_global_envs(self, bk_app, bk_module, envs):
        res = create_app_resource("foo", "nginx")
        res.spec.configuration.env = envs
        AppModelResource.objects.create_from_resource(bk_app.region, bk_app.id, bk_module.id, res)
        config_vars = EnvVarsReader(res).read_all(bk_module)

        for _var in config_vars:
            assert _var.environment_id == ENVIRONMENT_ID_FOR_GLOBAL

    @pytest.mark.parametrize(
        "overlays, expected_env",
        [
            ([EnvVarOverlay(name="Foo", value="2", envName="prod")], "prod"),
            ([EnvVarOverlay(name="bar", value="2", envName="stag")], "stag"),
        ],
    )
    def test_overlay(self, bk_app, bk_module, overlays, expected_env):
        res = create_app_resource("foo", "nginx")
        res.spec.envOverlay = EnvOverlay(envVariables=overlays)
        AppModelResource.objects.create_from_resource(bk_app.region, bk_app.id, bk_module.id, res)
        config_vars = EnvVarsReader(res).read_all(bk_module)
        for _var in config_vars:
            assert _var.environment == bk_module.get_envs(expected_env)
