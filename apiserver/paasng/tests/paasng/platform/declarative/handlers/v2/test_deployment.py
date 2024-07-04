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
from unittest import mock

import cattr
import pytest
import yaml

from paasng.platform.bkapp_model.models import get_svc_disc_as_env_variables
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import (
    AppDescriptionHandler,
    CNativeAppDescriptionHandler,
    SMartDescriptionHandler,
    get_desc_handler,
)
from paasng.platform.engine.configurations.config_var import get_preset_env_variables

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


class Test__get_desc_handler:
    """Test cases for `get_desc_handler()` function"""

    @pytest.mark.parametrize(
        ("yaml_fixture_name", "expected_type"),
        [
            ("yaml_v1_normal", SMartDescriptionHandler),
            ("yaml_v2_normal", AppDescriptionHandler),
            ("yaml_v3_normal", CNativeAppDescriptionHandler),
        ],
    )
    def test_v1(self, yaml_fixture_name, expected_type, request):
        _yaml_content = request.getfixturevalue(yaml_fixture_name)
        handler = get_desc_handler(yaml.safe_load(_yaml_content))
        assert isinstance(handler, expected_type)


class TestAppDescriptionHandler:
    def test_normal(self, bk_deployment, yaml_v2_normal):
        """Handle a normal YAML content."""
        with mock.patch(
            "paasng.platform.declarative.handlers.DeploymentDeclarativeController.update_bkmonitor"
        ) as update_bkmonitor:
            get_desc_handler(yaml.safe_load(yaml_v2_normal)).handle_deployment(bk_deployment)

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

    def test_with_modules_found(self, bk_deployment, bk_module):
        _yaml_content = dedent(
            f"""\
            spec_version: 2
            modules:
                {bk_module.name}:
                    language: python
        """
        )
        get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

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
            get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

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
        get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

    def test_with_module(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            module:
                language: python
        """
        )
        get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

    def test_with_module_and_modules_missing(self, bk_deployment):
        _yaml_content = dedent(
            """\
            spec_version: 2
            nothing: True
        """
        )
        with pytest.raises(DescriptionValidationError, match="配置内容不能为空"):
            get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)
