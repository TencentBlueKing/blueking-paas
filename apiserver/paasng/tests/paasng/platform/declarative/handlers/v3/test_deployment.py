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

import pytest
import yaml

from paas_wl.bk_app.cnative.specs.constants import PROC_SERVICES_ENABLED_ANNOTATION_KEY
from paasng.platform.bkapp_model.entities import ProcService
from paasng.platform.bkapp_model.models import ModuleProcessSpec, get_svc_disc_as_env_variables
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.configurations.config_var import get_preset_env_variables

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def yaml_v3_example() -> str:
    """An example of YAML content using v3 spec version."""
    return dedent(
        """
        specVersion: 3
        module:
          name: default
          language: python
          spec:
            configuration:
              env:
              - name: FOO
                value: 1
            processes:
              - name: web
                replicas: 1
                procCommand: python manage.py runserver
                services:
                - name: web
                  targetPort: 8000
                  port: 80
                  exposedType:
                    name: bk/http
                - name: backend
                  targetPort: 8001
            hooks:
              preRelease:
                procCommand: python manage.py migrate
            svcDiscovery:
                bkSaaS:
                  - bkAppCode: foo-app
                  - bkAppCode: bar-app
                    moduleName: api
    """
    )


class TestCnativeAppDescriptionHandler:
    def test_handle_deployment_normal(self, bk_deployment, yaml_v3_example):
        with mock.patch(
            "paasng.platform.declarative.handlers.DeploymentDeclarativeController.update_bkmonitor"
        ) as update_bkmonitor:
            handler = get_desc_handler(yaml.safe_load(yaml_v3_example))

            handler.handle_deployment(bk_deployment)

            deploy_desc = handler.get_deploy_desc(bk_deployment.app_environment.module.name)
            assert deploy_desc.get_procfile() == {"web": "python manage.py runserver"}

            assert bk_deployment.hooks[0].command == []
            assert bk_deployment.hooks[0].args == ["python", "manage.py", "migrate"]

            # 测试 specVersion: 3, 正确记录 bkapp.paas.bk.tencent.com/proc-services-feature-enabled: true
            desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
            assert desc_obj.runtime[PROC_SERVICES_ENABLED_ANNOTATION_KEY] == "true"

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

            spec = ModuleProcessSpec.objects.get(module=bk_deployment.app_environment.module, name="web")
            assert spec.services == [
                ProcService(
                    name="web",
                    target_port=8000,
                    protocol="TCP",
                    exposed_type={"name": "bk/http"},
                    port=80,
                ),
                ProcService(name="backend", target_port=8001, protocol="TCP", exposed_type=None, port=8001),
            ]

            assert not update_bkmonitor.called

    def test_with_modules_found(self, bk_deployment, bk_module):
        _yaml_content = dedent(
            f"""\
            specVersion: 3
            modules:
              - name: {bk_module.name}
                language: python
                spec:
                  processes:
                    - name: web
                      replicas: 1
                      procCommand: python manage.py runserver
        """
        )
        get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

    def test_with_modules_not_found(self, bk_deployment):
        _yaml_content = dedent(
            """\
            specVersion: 3
            modules:
              - name: wrong-module-name
                language: python
                spec:
                  processes:
                    - name: web
                      replicas: 1
                      procCommand: python manage.py runserver
        """
        )
        with pytest.raises(DescriptionValidationError, match="未找到.*当前已配置"):
            get_desc_handler(yaml.safe_load(_yaml_content)).handle_deployment(bk_deployment)

    # Other tests that cover different cases when modules/module field uses different values
    # share similar logic with TestAppDescriptionHandler, no need to duplicate in here.
