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

import base64
import json
from textwrap import dedent
from typing import Dict, Tuple
from unittest import mock

import cattr
import pytest
import yaml
from django_dynamic_fixture import G

from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec, get_svc_disc_as_env_variables
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_deploy_desc_handler
from paasng.platform.engine.configurations.config_var import get_preset_env_variables
from paasng.platform.modules.models.module import Module

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def yaml_v1_normal() -> str:
    """A sample YAML content using v1 spec version."""
    return dedent(
        """
        version: 1
        module:
            language: python
            env_variables:
                - key: BKPAAS_RESERVED_KEY
                  value: raise error
    """
    )


@pytest.fixture()
def yaml_v2_normal() -> str:
    """A sample YAML content using v2 spec version."""
    return dedent(
        """
        spec_version: 2
        module:
            env_variables:
                - key: FOO
                  value: 1
            language: python
            svc_discovery:
                bk_saas:
                - foo-app
                - bk_app_code: bar-app
                  module_name: api
            bkmonitor:
                port: 80
    """
    )


@pytest.fixture()
def yaml_v3_normal() -> str:
    """A sample YAML content using v3 spec version."""
    return dedent(
        """
        specVersion: 3
        module:
          name: default
          language: python
          spec:
            processes:
              - name: web
                replicas: 1
                procCommand: python manage.py runserver
    """
    )


class Test__get_deploy_desc_handler:
    """Test cases for `get_desc_handler()` function"""

    @pytest.mark.parametrize(
        ("yaml_fixture_name", "expected_name"),
        [
            ("yaml_v1_normal", "deploy_desc_getter_v1"),
            ("yaml_v2_normal", "deploy_desc_getter_v2"),
            ("yaml_v3_normal", "deploy_desc_getter_v3"),
        ],
    )
    def test_desc_getter_name(self, yaml_fixture_name, expected_name, request):
        _yaml_content = request.getfixturevalue(yaml_fixture_name)
        handler = get_deploy_desc_handler(yaml.safe_load(_yaml_content))
        assert hasattr(handler, "desc_getter")
        assert handler.desc_getter.__name__ == expected_name


class TestAppDescriptionHandler:
    @pytest.fixture()
    def _create_for_test_svc_discovery(self):
        # 为了检验 BKPAAS_SERVICE_ADDRESSES_BKSAAS 通过
        G(Application, code="foo-app")
        app = G(Application, code="bar-app")
        G(Module, name="api", application=app)

    @pytest.mark.usefixtures("_create_for_test_svc_discovery")
    def test_normal(self, bk_deployment, yaml_v2_normal):
        """Handle a normal YAML content."""

        with mock.patch(
            "paasng.platform.declarative.handlers.DeploymentDeclarativeController._update_bkmonitor"
        ) as update_bkmonitor:
            get_deploy_desc_handler(yaml.safe_load(yaml_v2_normal)).handle(bk_deployment)

            assert get_preset_env_variables(bk_deployment.app_environment) == {"FOO": "1"}
            assert get_svc_disc_as_env_variables(bk_deployment.app_environment) == {
                "BKPAAS_SERVICE_ADDRESSES_BKSAAS": base64.b64encode(
                    json.dumps(
                        [
                            {
                                "key": {"bk_app_code": "foo-app", "module_name": None},
                                "value": {
                                    "stag": "http://stag-dot-foo-app.bkapps.example.com",
                                    "prod": "http://foo-app.bkapps.example.com",
                                },
                            },
                            {
                                "key": {"bk_app_code": "bar-app", "module_name": "api"},
                                "value": {
                                    "stag": "http://stag-dot-api-dot-bar-app.bkapps.example.com",
                                    "prod": "http://prod-dot-api-dot-bar-app.bkapps.example.com",
                                },
                            },
                        ]
                    ).encode()
                ).decode()
            }

            assert update_bkmonitor.called
            assert cattr.unstructure(update_bkmonitor.call_args[0][0]) == {"port": 80, "target_port": 80}

    def test_desc_and_procfile_same(self, bk_module, bk_deployment):
        content = dedent(
            """
            spec_version: 2
            module:
                language: python
                processes:
                    web:
                      command: python manage.py runserver
                      replicas: 3
            """
        )
        handler = get_deploy_desc_handler(yaml.safe_load(content), procfile_data={"web": "python manage.py runserver"})
        ret = handler.handle(bk_deployment)

        assert query_proc_dict(bk_module) == {"web": ("python manage.py runserver", 3)}
        assert ret.processes
        assert len(ret.processes) == 1

    def test_desc_and_procfile_different(self, bk_module, bk_deployment):
        content = dedent(
            """
            spec_version: 2
            module:
                language: python
                processes:
                    web:
                      command: python manage.py runserver
                      replicas: 3
            """
        )
        handler = get_deploy_desc_handler(
            yaml.safe_load(content), procfile_data={"web": "gunicorn app", "worker": "celery"}
        )
        ret = handler.handle(bk_deployment)

        assert query_proc_dict(bk_module) == {"web": ("gunicorn app", 1), "worker": ("celery", 1)}
        assert ret.processes
        assert len(ret.processes) == 2

    def test_procfile_only(self, bk_module, bk_deployment):
        handler = get_deploy_desc_handler(None, procfile_data={"web": "gunicorn app", "worker": "celery"})
        ret = handler.handle(bk_deployment)

        assert query_proc_dict(bk_module) == {"web": ("gunicorn app", 1), "worker": ("celery", 1)}
        assert ret.processes
        assert len(ret.processes) == 2

    def test_invalid_desc_and_valid_procfile(self, bk_module, bk_deployment):
        handler = get_deploy_desc_handler(
            {"not": "valid yaml"}, procfile_data={"web": "gunicorn app", "worker": "celery"}
        )
        ret = handler.handle(bk_deployment, ignore_invalid_desc=True)

        assert query_proc_dict(bk_module) == {"web": ("gunicorn app", 1), "worker": ("celery", 1)}
        assert ret.processes
        assert len(ret.processes) == 2

    def test_with_modules_found(self, bk_deployment, bk_module):
        _yaml_content = dedent(
            f"""\
            spec_version: 2
            modules:
                {bk_module.name}:
                    language: python
        """
        )
        get_deploy_desc_handler(yaml.safe_load(_yaml_content)).handle(bk_deployment)

    def test_with_modules_not_found(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            modules:
                wrong-module-name:
                    language: python
        """
        )
        with pytest.raises(DescriptionValidationError, match="未找到.*当前已配置"):
            get_deploy_desc_handler(yaml.safe_load(_yaml_content)).handle(bk_deployment)

    def test_with_modules_not_found_fallback_to_module(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            modules:
                wrong-module-name:
                    language: python
            module:
                language: python
        """
        )
        get_deploy_desc_handler(yaml.safe_load(_yaml_content)).handle(bk_deployment)

    def test_with_module(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            module:
                language: python
        """
        )
        get_deploy_desc_handler(yaml.safe_load(_yaml_content)).handle(bk_deployment)

    def test_with_module_and_modules_missing(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            nothing: True
        """
        )
        with pytest.raises(DescriptionValidationError, match="配置内容不能为空"):
            get_deploy_desc_handler(yaml.safe_load(_yaml_content)).handle(bk_deployment)


def query_proc_dict(module: Module) -> Dict[str, Tuple[str, int]]:
    """A helper function that queries module's all process specs for comparison."""
    proc_dict = {}
    for p in ModuleProcessSpec.objects.filter(module=module):
        proc_dict[p.name] = (p.proc_command, p.target_replicas)
    return proc_dict
