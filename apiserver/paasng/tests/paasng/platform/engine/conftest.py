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
from django.test.utils import override_settings
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.models import BuildProcess, WlApp
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ENVIRONMENT_NAME_FOR_GLOBAL, ConfigVar
from tests.paas_wl.utils.build import create_build_proc


@pytest.fixture(autouse=True, scope="session")
def _no_color():
    with override_settings(COLORFUL_TERMINAL_OUTPUT=False):
        yield


@pytest.fixture()
def wl_app(bk_stag_env, _with_wl_apps) -> WlApp:
    """A WlApp object"""
    return bk_stag_env.wl_app


@pytest.fixture()
def build_proc(wl_app) -> BuildProcess:
    """A new BuildProcess object with random info"""
    env = ModuleEnvironment.objects.get(engine_app_id=wl_app.uuid)
    return create_build_proc(env)


@pytest.fixture()
def config_var_maker():
    """A shortcut fixture for creating ConfigVar objects."""

    def maker(environment_name, module, **kwargs):
        kwargs["module"] = module
        if environment_name == ENVIRONMENT_NAME_FOR_GLOBAL:
            kwargs["environment"] = None
            kwargs["is_global"] = True
            kwargs["environment_id"] = ENVIRONMENT_ID_FOR_GLOBAL
        else:
            kwargs["environment"] = module.get_envs(environment_name)
            kwargs["is_global"] = False

        var = G(ConfigVar, **kwargs)
        # G 不支持设置 environment_id
        if environment_name == ENVIRONMENT_NAME_FOR_GLOBAL:
            var.environment_id = ENVIRONMENT_ID_FOR_GLOBAL
            var.save()
        return var

    return maker
