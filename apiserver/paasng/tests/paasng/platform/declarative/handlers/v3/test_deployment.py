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
import base64
import json
from textwrap import dedent
from unittest import mock

import pytest
import yaml
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.platform.bkapp_model.models import get_svc_disc_as_env_variables
from paasng.platform.declarative.handlers import CNativeAppDescriptionHandler, DescriptionHandler
from paasng.platform.declarative.handlers import get_desc_handler as _get_desc_handler
from paasng.platform.engine.configurations.config_var import get_preset_env_variables

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_desc_handler(yaml_content: str) -> DescriptionHandler:
    handler = _get_desc_handler(yaml.safe_load(yaml_content))
    assert isinstance(handler, CNativeAppDescriptionHandler), "handler is not CNativeAppDescriptionHandler"
    return handler


class TestAppDescriptionHandler:
    @pytest.mark.parametrize(
        ("yaml_content", "ctx"),
        [
            (
                dedent(
                    """
                spec_version: 3
                module:
                  name: default
                  language: python
                  spec:
                    configuration:
                      env:
                      - name: FOO
                        value: 1
                    svcDiscovery:
                      bkSaaS:
                      - bkAppCode: foo-app
                      - bkAppCode: bar-app
                        moduleName: api
                """
                ),
                does_not_raise(
                    {
                        "env_variables": {"FOO": "1"},
                        "svc_discovery": {
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
                        },
                    }
                ),
            ),
            (
                dedent(
                    """
                    version: 1
                    module:
                        language: python
                        env_variables:
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                    """
                ),
                pytest.raises(AssertionError, match="handler is not CNativeAppDescriptionHandler"),
            ),
        ],
    )
    def test_deployment_normal(self, bk_deployment, yaml_content, ctx):
        with ctx as expected, mock.patch(
            "paasng.platform.declarative.handlers.DeploymentDeclarativeController.update_bkmonitor"
        ) as update_bkmonitor:
            get_desc_handler(yaml_content).handle_deployment(bk_deployment)
            assert get_preset_env_variables(bk_deployment.app_environment) == expected["env_variables"]
            assert get_svc_disc_as_env_variables(bk_deployment.app_environment) == expected["svc_discovery"]
            assert not update_bkmonitor.called
