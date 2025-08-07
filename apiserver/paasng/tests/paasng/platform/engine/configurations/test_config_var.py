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

from textwrap import dedent

import pytest
import yaml
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings
from django_dynamic_fixture import G

from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_deploy_desc_handler
from paasng.platform.engine.configurations.config_var import (
    EnvVarSource,
    UnifiedEnvVarsReader,
    get_builtin_env_variables,
    get_env_variables,
    list_conflicted_env_vars_for_view,
    list_vars_builtin_runtime,
)
from paasng.platform.engine.models.config_var import BuiltinConfigVar, ConfigVar
from paasng.platform.modules.models.module import Module
from tests.utils.helpers import override_region_configs

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.usefixtures("_with_wl_apps")
class TestGetEnvVariables:
    @pytest.fixture()
    def _create_for_test_svc_discovery(self):
        # 为了检验 BKPAAS_SERVICE_ADDRESSES_BKSAAS 通过
        G(Application, code="foo-app")
        app = G(Application, code="bar-app")
        G(Module, name="api", application=app)

    def test_normal_config_var(self, bk_module, bk_stag_env):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO", value="bar")
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars["FOO"] == "bar"

    def test_builtin_id_and_secret(self, bk_app, bk_stag_env):
        env_vars = get_env_variables(bk_stag_env)

        assert env_vars["BKPAAS_APP_ID"] == bk_app.code
        assert env_vars["BKPAAS_APP_SECRET"] != ""

    def test_wl_vars_exists(self, bk_stag_env):
        env_vars = get_env_variables(bk_stag_env)

        assert env_vars["PORT"] != ""
        assert env_vars["BKPAAS_PROCESS_TYPE"] != ""

    @pytest.mark.parametrize(
        ("yaml_content", "ctx"),
        [
            (
                dedent(
                    """
                    spec_version: 2
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
                    spec_version: 2
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
                    spec_version: 2
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
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO", value="bar")
        with ctx as expected:
            get_deploy_desc_handler(yaml.safe_load(yaml_content)).handle(bk_deployment)
            env_vars = get_env_variables(bk_stag_env)
            for key, value in expected.items():
                assert key in env_vars
                assert env_vars[key] == value

    @pytest.mark.usefixtures("_create_for_test_svc_discovery")
    def test_part_saas_services(self, bk_stag_env, bk_deployment):
        yaml_content = dedent(
            """
            spec_version: 2
            module:
                svc_discovery:
                    bk_saas:
                        - bk_app_code: foo-app
                        - bk_app_code: bar-app
                          module_name: api
                language: python
            """
        )
        get_deploy_desc_handler(yaml.safe_load(yaml_content)).handle(bk_deployment)
        env_vars = get_env_variables(bk_stag_env)
        assert "BKPAAS_SERVICE_ADDRESSES_BKSAAS" in env_vars


@pytest.mark.usefixtures("_with_wl_apps")
class TestUserVarsConflictsWithBuiltIn:
    """测试当用户自定义的环境变量与系统内置的环境变量冲突时，行为是否符合预期。"""

    def test_should_overwrite_builtin_vars(self, bk_module, bk_stag_env):
        """用户定义的环境变量应当覆盖内置的环境变量。

        - 仅覆盖普通应用的逻辑，因为只有普通应用才会不带参数调用 get_env_variables() 来获得带 ConfigVar 的结果。
        - 云原生应用采用其他方式合并环境变量，并且是以内置变量最为优先（见 `test_builtin_env_has_high_priority()`），
          两类应用的这个行为差异主要是历史原因造成，因为调整会影响存量应用行为，所以暂无修复计划。
        """
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="BK_API_URL_TMPL", value="(new_value)")

        env_vars = get_env_variables(bk_stag_env)
        assert env_vars["BK_API_URL_TMPL"] == "(new_value)"


@pytest.mark.usefixtures("_with_wl_apps")
class TestBuiltInEnvVars:
    @pytest.mark.parametrize(("provide_env_vars_platform", "contain_bk_envs"), [(True, True), (False, True)])
    def test_bk_platform_envs(self, bk_app, provide_env_vars_platform, contain_bk_envs):
        def update_region_hook(config):
            config["provide_env_vars_platform"] = provide_env_vars_platform

        with override_region_configs(bk_app.region, update_region_hook):
            bk_module = bk_app.get_default_module()
            bk_stag_env = bk_module.envs.get(environment="stag")
            config_vars = get_builtin_env_variables(bk_stag_env.engine_app).kv_map

            # 这些环境变量在所有版本都有
            assert ("BK_COMPONENT_API_URL" in config_vars) == contain_bk_envs
            assert ("BK_PAAS2_URL" in config_vars) == contain_bk_envs
            assert ("BK_API_URL_TMPL" in config_vars) == contain_bk_envs

            # BK_LOGIN_URL 只在特殊开启的版本才写入
            assert ("BK_LOGIN_URL" in config_vars) == provide_env_vars_platform
            # 应用是需要写入蓝鲸体系其他系统访问地址的环境变量
            if provide_env_vars_platform:
                assert set(settings.BK_PAAS2_PLATFORM_ENVS.keys()).issubset(set(config_vars.keys())) == contain_bk_envs

            # 环境变量中的 bool 值需要转为小写开头字符串
            assert config_vars["BKPAAS_MULTI_TENANT_MODE"] == "false"

    def test_builtin_env_keys(self, bk_stag_env):
        config_vars = get_builtin_env_variables(bk_stag_env.engine_app).kv_map

        assert {
            "BKPAAS_LOGIN_URL",
            "BKPAAS_APP_CODE",
            "BKPAAS_APP_ID",
            "BKPAAS_APP_SECRET",
            "BKPAAS_APP_TENANT_ID",
            # 运行时相关变量
            "BKPAAS_APP_MODULE_NAME",
            "BKPAAS_ENVIRONMENT",
            "BKPAAS_MAJOR_VERSION",
            "BKPAAS_ENGINE_REGION",
        }.issubset(config_vars.keys())

    def test_param_include_custom_builtin_config_vars(self, bk_stag_env):
        BuiltinConfigVar.objects.create(key="FOO", value="bar")
        # test overwrite
        BuiltinConfigVar.objects.create(key="LOGIN_URL", value="bar")
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars["BKPAAS_LOGIN_URL"] == "bar"
        assert env_vars["BKPAAS_FOO"] == "bar"


@pytest.mark.usefixtures("_with_wl_apps")
def test_list_vars_builtin_runtime(bk_app, bk_stag_env):
    env_vars = list_vars_builtin_runtime(bk_stag_env).kv_map

    assert "PORT" in env_vars
    assert "BKPAAS_APP_LOG_PATH" in env_vars
    assert "BKPAAS_SUB_PATH" in env_vars
    assert env_vars["BKPAAS_PROCESS_TYPE"] == "{{bk_var_process_type}}"
    assert env_vars["BKPAAS_LOG_NAME_PREFIX"].endswith("-{{bk_var_process_type}}")
    assert env_vars["BKPAAS_ENGINE_REGION"] == bk_app.region


@pytest.mark.usefixtures("_with_wl_apps")
class Test__list_conflicted_env_vars_for_view:
    @pytest.mark.parametrize(
        ("app_type", "expected_override_conflicted"),
        [(ApplicationType.DEFAULT, True), (ApplicationType.CLOUD_NATIVE, False)],
    )
    def test_list_conflicted_env_vars_for_view(self, bk_module, bk_stag_env, app_type, expected_override_conflicted):
        bk_module.application.type = app_type
        bk_module.application.save(update_fields=["type"])
        # 因为 list_vars_builtin_runtime 列出的 EnvVariableList 属于 EnvVarSource.BUILTIN_MISC
        # 在 云原生应用 中会将 override_conflicted 修改为 False
        # 在 非云原生应用 中 override_conflicted 为 True
        result = list_conflicted_env_vars_for_view(bk_module)
        assert isinstance(result, list)
        assert any(item.override_conflicted is expected_override_conflicted for item in result)


@pytest.mark.usefixtures("_with_wl_apps")
class TestUnifiedEnvVarsReader:
    def test_exclude_sources(self, bk_module, bk_stag_env):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key="FOO", value="bar")

        env_vars = UnifiedEnvVarsReader(bk_stag_env).get_kv_map()
        assert env_vars["FOO"] == "bar"

        env_vars = UnifiedEnvVarsReader(bk_stag_env).get_kv_map(exclude_sources=[EnvVarSource.USER_CONFIGURED])
        assert "FOO" not in env_vars

    def test_list_conflicted_info_normal(self, bk_module, bk_stag_env):
        vars_reader = UnifiedEnvVarsReader(bk_stag_env)

        conflicts = vars_reader.list_conflicted_info()

        assert isinstance(conflicts, list)
        assert any(item.override_conflicted is not None for item in conflicts)

    def test_list_conflicted_info_exclude_sources(self, bk_module, bk_stag_env):
        vars_reader = UnifiedEnvVarsReader(bk_stag_env)

        conflicts = vars_reader.list_conflicted_info(exclude_sources=[EnvVarSource.BUILTIN_MISC])

        assert isinstance(conflicts, list)
        assert any(item.override_conflicted is not None for item in conflicts)
