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
import io
from textwrap import dedent
from unittest import mock

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.engine.configurations.config_var import get_env_variables
from paasng.engine.models.config_var import ConfigVar
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler
from tests.utils.mocks.engine import mock_cluster_service

pytestmark = pytest.mark.django_db


class TestGetEnvVariables:
    @pytest.fixture(autouse=True)
    def setup_cluster(self):
        with mock_cluster_service():
            yield

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks for current testing module

        - Mock ProcessManager which depends on `workloads` module
        """
        with mock.patch('paasng.extensions.declarative.deployment.controller.ProcessManager'):
            yield

    def test_user_config_var(self, bk_module, bk_stag_env):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO', value='bar')
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars['FOO'] == 'bar'

    def test_builtin_id_and_secret(self, bk_app, bk_stag_env):
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars['BKPAAS_APP_ID'] == bk_app.code
        assert env_vars['BKPAAS_APP_SECRET'] != ''

    @pytest.mark.parametrize(
        "yaml_content, ctx",
        [
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                        language: python
                    '''
                ),
                does_not_raise({"FOO_DESC": "bar"}),
            ),
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO
                              value: will be overwrite
                        language: python
                    '''
                ),
                does_not_raise({"FOO": "bar"}),
            ),
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                        language: python
                    '''
                ),
                pytest.raises(DescriptionValidationError),
            ),
        ],
    )
    def test_part_declarative(self, bk_module, bk_stag_env, bk_app, bk_deployment, yaml_content, ctx):
        fp = io.StringIO(yaml_content)
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO', value='bar')
        with ctx as expected:
            AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
            env_vars = get_env_variables(bk_stag_env, deployment=bk_deployment)
            for key, value in expected.items():
                assert key in env_vars
                assert env_vars[key] == value

    def test_part_saas_services(self, bk_stag_env, bk_deployment):
        yaml_content = dedent(
            '''
            version: 1
            module:
                svc_discovery:
                    bk_saas:
                        - bk_app_code: foo-app
                        - bk_app_code: bar-app
                          module_name: api
                language: python
            '''
        )
        fp = io.StringIO(yaml_content)
        AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
        env_vars = get_env_variables(bk_stag_env, deployment=bk_deployment)
        assert 'BKPAAS_SERVICE_ADDRESSES_BKSAAS' in env_vars
