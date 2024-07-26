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

import io
from textwrap import dedent

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings

from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import AppDescriptionHandler
from paasng.platform.engine.configurations.config_var import get_builtin_env_variables, get_env_variables
from paasng.platform.engine.constants import AppRunTimeBuiltinEnv
from paasng.platform.engine.models.config_var import BuiltinConfigVar, ConfigVar
from tests.utils.helpers import override_region_configs

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestGetEnvVariables:
    @pytest.mark.parametrize(
        ("include_config_vars", "ctx"), [(True, does_not_raise("bar")), (False, pytest.raises(KeyError))]
    )
    def test_param_include_config_vars(self, bk_module, bk_stag_env, include_config_vars, ctx):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO", value="bar")
        env_vars = get_env_variables(bk_stag_env, include_config_vars=include_config_vars)
        with ctx as expected:
            assert env_vars["FOO"] == expected

    def test_builtin_id_and_secret(self, bk_app, bk_stag_env):
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars["BKPAAS_APP_ID"] == bk_app.code
        assert env_vars["BKPAAS_APP_SECRET"] != ""

    @pytest.mark.parametrize(
        ("yaml_content", "ctx"),
        [
            (
                dedent(
                    """
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                        language: python
                    """
                ),
                does_not_raise({"FOO_DESC": "bar"}),
            ),
            (
                dedent(
                    """
                    version: 1
                    module:
                        env_variables:
                            - key: FOO
                              value: will be overwrite
                        language: python
                    """
                ),
                does_not_raise({"FOO": "bar"}),
            ),
            (
                dedent(
                    """
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                        language: python
                    """
                ),
                pytest.raises(DescriptionValidationError),
            ),
        ],
    )
    def test_part_declarative(self, bk_module, bk_stag_env, bk_app, bk_deployment, yaml_content, ctx):
        fp = io.StringIO(yaml_content)
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO", value="bar")
        with ctx as expected:
            AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
            env_vars = get_env_variables(bk_stag_env)
            for key, value in expected.items():
                assert key in env_vars
                assert env_vars[key] == value

    def test_part_saas_services(self, bk_stag_env, bk_deployment):
        yaml_content = dedent(
            """
            version: 1
            module:
                svc_discovery:
                    bk_saas:
                        - bk_app_code: foo-app
                        - bk_app_code: bar-app
                          module_name: api
                language: python
            """
        )
        fp = io.StringIO(yaml_content)
        AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
        env_vars = get_env_variables(bk_stag_env)
        assert "BKPAAS_SERVICE_ADDRESSES_BKSAAS" in env_vars


class TestBuiltInEnvVars:
    @pytest.mark.parametrize(("provide_env_vars_platform", "contain_bk_envs"), [(True, True), (False, True)])
    def test_bk_platform_envs(self, bk_app, provide_env_vars_platform, contain_bk_envs):
        def update_region_hook(config):
            config["provide_env_vars_platform"] = provide_env_vars_platform

        with override_region_configs(bk_app.region, update_region_hook):
            bk_module = bk_app.get_default_module()
            bk_stag_env = bk_module.envs.get(environment="stag")
            config_vars = get_builtin_env_variables(bk_stag_env.engine_app, settings.CONFIGVAR_SYSTEM_PREFIX)

            # 这些环境变量在所有版本都有
            assert ("BK_COMPONENT_API_URL" in config_vars) == contain_bk_envs
            assert ("BK_PAAS2_URL" in config_vars) == contain_bk_envs
            assert ("BK_API_URL_TMPL" in config_vars) == contain_bk_envs

            # BK_LOGIN_URL 只在特殊开启的版本才写入
            assert ("BK_LOGIN_URL" in config_vars) == provide_env_vars_platform
            # 应用是需要写入蓝鲸体系其他系统访问地址的环境变量
            if provide_env_vars_platform:
                assert set(settings.BK_PAAS2_PLATFORM_ENVS.keys()).issubset(set(config_vars.keys())) == contain_bk_envs

    def test_builtin_env_keys(self, bk_app):
        bk_module = bk_app.get_default_module()
        bk_stag_env = bk_module.envs.get(environment="stag")
        config_vars = get_builtin_env_variables(bk_stag_env.engine_app, settings.CONFIGVAR_SYSTEM_PREFIX)

        assert {"BKPAAS_LOGIN_URL", "BKPAAS_APP_CODE", "BKPAAS_APP_ID", "BKPAAS_APP_SECRET"}.issubset(
            config_vars.keys()
        )

        # 运行时相关的环境变量，其中 DEFAULT_PREALLOCATED_URLS 是在 _default_preallocated_urls() 中单独处理的环境变量
        runtime_env_keys = [
            f"{settings.CONFIGVAR_SYSTEM_PREFIX}{key}"
            for key in AppRunTimeBuiltinEnv.get_values()
            if key != AppRunTimeBuiltinEnv.DEFAULT_PREALLOCATED_URLS.value
        ]
        assert set(runtime_env_keys).issubset(config_vars.keys())

    def test_param_include_custom_builtin_config_vars(self, bk_stag_env):
        BuiltinConfigVar.objects.create(key="FOO", value="bar")
        env_vars = get_env_variables(bk_stag_env)
        with does_not_raise("bar") as expected:
            assert env_vars["BKPAAS_FOO"] == expected
