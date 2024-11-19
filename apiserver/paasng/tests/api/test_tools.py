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
import yaml
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def app_desc_yaml():
    return """
    spec_version: 2
    app_version: "1.0"
    app:
      region: default
      bk_app_code: "foo-app"
      bk_app_name: 默认应用名称
      market:
        category: 运维工具
        introduction: 应用简介
        description: 应用描述
        display_options:
          width: 800
          height: 600
          open_mode: desktop
          is_win_maximize: False
          visible: True
    modules:
      frontend:
        is_default: True
        source_dir: src/frontend
        language: NodeJS
        services: # 增强服务配置仅对 Smart 应用生效
          - name: mysql
          - name: rabbitmq
        env_variables:
          - key: FOO
            value: value_of_foo
            description: 环境变量描述文件
        processes:
          web:
            command: npm run server
            plan: 4C1G5R
            replicas: 2 # 副本数不能超过 plan 中定义的值
            probes:
              liveness:
                exec:
                  command:
                    - cat
              readiness:
                http_get:
                  path: /healthz
                  port: 80
        scripts:
          pre_release_hook: bin/pre-release.sh
        svc_discovery:
          bk_saas:
            - "bk-iam"
            - "bk-user"
      api_server:
        is_default: False
        source_dir: src/backend
        language: Python
        services: # 增强服务配置仅对 Smart 应用生效
          - name: mysql
            share_from: default
          - name: rabbitmq
            share_from: default
        env_variables:
          - key: FOO
            value: value_of_foo
            description: 环境变量描述文件
        processes:
          web:
            command: python manage.py runserver
            plan: 4C1G5R
            replicas: 2 # 副本数不能超过 plan 中定义的值
            probes:
              liveness:
                exec:
                  command:
                    - "/bin/bash"
                    - "-c"
                    - "echo ready"
              readiness:
                http_get:
                  path: /healthz
                  port: 80
                  http_headers:
                    - name: Content-Type
                    - value: application/json
              startup:
                tcpscoket:
                  port: 8000
                  host: app.host.com
                initial_delay_seconds: 0
                timeout_seconds: 1
                period_seconds: 10
                success_threshold: 1
                failure_threshold: 3
        scripts:
          pre_release_hook: python manage.py migrate
        svc_discovery:
          bk_saas:
            - bk_app_code: "bk-iam"
            - bk_app_code: "bk-user"
              module_name: "api"
        package_plans:
          web: Starter
    """


class TestAppDescTransform:
    def test_app_desc_transform(self, api_client, app_desc_yaml):
        """测试应用描述文件转换接口"""
        response = api_client.post(
            reverse("api.tools.app_desc.transform"), data=app_desc_yaml, content_type="application/yaml"
        )

        output_data = yaml.safe_load(response.content)
        input_data = yaml.safe_load(app_desc_yaml)

        assert output_data["specVersion"] == 3
        assert output_data["appVersion"] == input_data["app_version"]
        assert output_data["modules"][0]["name"] == list(input_data["modules"].keys())[0]
        assert output_data["modules"][0]["spec"]["processes"][0]["name"] == "web"
        assert output_data["modules"][1]["name"] == list(input_data["modules"].keys())[1]
        assert output_data["modules"][1]["spec"]["hooks"]["preRelease"]["procCommand"] == "python manage.py migrate"
