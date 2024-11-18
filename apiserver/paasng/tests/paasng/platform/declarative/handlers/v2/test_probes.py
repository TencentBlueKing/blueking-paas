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

from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.handlers import get_deploy_desc_handler

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def yaml_content():
    return dedent(
        """
        spec_version: 2
        app_version: "1.0"
        app:
            region: default
            bk_app_code: "foo-app"
            bk_app_name: 默认应用名称
            bk_app_name_en: default-app-name
        modules:
            default:
                source_dir: src/frontend
                language: NodeJS
                processes:
                    web:
                        command: npm run server
                        plan: 4C1G5R
                        replicas: 2
                        probes:
                            liveness:
                                exec:
                                    command:
                                    - cat
                                    - /tmp/healthy
                            readiness:
                                tcp_socket:
                                    port: ${PORT}
        """
    )


@pytest.fixture()
def yaml_content_after_change():
    return dedent(
        """
        spec_version: 2
        app_version: "1.0"
        app:
            region: default
            bk_app_code: "foo-app"
            bk_app_name: 默认应用名称
            bk_app_name_en: default-app-name
        modules:
            default:
                source_dir: src/frontend
                language: NodeJS
                processes:
                    web:
                        command: npm run server
                        plan: 4C1G5R
                        replicas: 2
                        probes:
                            liveness:
                                exec:
                                    command:
                                    - cat
                                    - /tmp/healthy
                            startup:
                                tcp_socket:
                                    port: ${PORT}
        """
    )


class TestSaasProbes:
    def test_process_spec_should_have_probes(self, bk_module, bk_deployment, yaml_content):
        get_handler(yaml_content).handle(bk_deployment)

        spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")

        assert spec.probes.liveness.exec.command == ["cat", "/tmp/healthy"]
        assert spec.probes.readiness.tcp_socket.port == "${PORT}"

    def test_probes_changes_after_handling_new_yaml(
        self, bk_module, bk_deployment, bk_deployment_full, yaml_content, yaml_content_after_change
    ):
        # bk_deployment.app_environment  外键未实例化，补全
        name = bk_deployment.app_environment.engine_app.name
        region = bk_deployment.app_environment.engine_app.region

        # bk_deployment_full.app_environment  外键未实例化，补全
        bk_deployment_full.app_environment.engine_app.name = name
        bk_deployment_full.app_environment.engine_app.region = region

        get_handler(yaml_content).handle(bk_deployment)
        # 模拟重新部署过程
        get_handler(yaml_content_after_change).handle(bk_deployment)

        spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert spec.probes.liveness.exec.command == ["cat", "/tmp/healthy"]
        assert not spec.probes.readiness
        assert spec.probes.startup.tcp_socket.port == "${PORT}"


def get_handler(yaml_content: str):
    return get_deploy_desc_handler(yaml.safe_load(yaml_content))
