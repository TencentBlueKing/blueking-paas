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
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestAppDescTransform:
    @pytest.mark.parametrize(
        ("spec2_yaml", "expected_spec3_data", "expected_spec3_yaml"),
        [
            # Test 1: two modules
            (
                """spec_version: 2
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
      - key: FOO1
        value: ''
        description: 测试空值
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
      server:
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
            tcp_socket:
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
""",
                {
                    "specVersion": 3,
                    "appVersion": "1.0",
                    "app": {
                        "region": "default",
                        "bkAppCode": "foo-app",
                        "bkAppName": "默认应用名称",
                        "market": {
                            "category": "运维工具",
                            "introduction": "应用简介",
                            "description": "应用描述",
                            "displayOptions": {
                                "width": 800,
                                "height": 600,
                                "openMode": "desktop",
                                "isWinMaximize": False,
                                "visible": True,
                            },
                        },
                    },
                    "modules": [
                        {
                            "name": "frontend",
                            "isDefault": True,
                            "sourceDir": "src/frontend",
                            "language": "NodeJS",
                            "spec": {
                                "addons": [{"name": "mysql"}, {"name": "rabbitmq"}],
                                "configuration": {
                                    "env": [
                                        {"name": "FOO", "value": "value_of_foo", "description": "环境变量描述文件"},
                                        {"name": "FOO1", "value": "", "description": "测试空值"},
                                    ]
                                },
                                "processes": [
                                    {
                                        "name": "web",
                                        "procCommand": "npm run server",
                                        "resQuotaPlan": "4C1G",
                                        "replicas": 2,
                                        "probes": {
                                            "liveness": {"exec": {"command": ["cat"]}},
                                            "readiness": {"httpGet": {"path": "/healthz", "port": 80}},
                                        },
                                        "services": [
                                            {
                                                "name": "web",
                                                "protocol": "TCP",
                                                "exposedType": {"name": "bk/http"},
                                                "targetPort": settings.CONTAINER_PORT,
                                                "port": 80,
                                            }
                                        ],
                                    }
                                ],
                                "hooks": {"preRelease": {"procCommand": "bin/pre-release.sh"}},
                                "svcDiscovery": {"bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user"}]},
                            },
                        },
                        {
                            "name": "api_server",
                            "isDefault": False,
                            "sourceDir": "src/backend",
                            "language": "Python",
                            "spec": {
                                "addons": [
                                    {"name": "mysql", "shareFrom": "default"},
                                    {"name": "rabbitmq", "shareFrom": "default"},
                                ],
                                "configuration": {
                                    "env": [
                                        {"name": "FOO", "value": "value_of_foo", "description": "环境变量描述文件"}
                                    ]
                                },
                                "processes": [
                                    {
                                        "name": "server",
                                        "procCommand": "python manage.py runserver",
                                        "resQuotaPlan": "4C1G",
                                        "replicas": 2,
                                        "probes": {
                                            "liveness": {"exec": {"command": ["/bin/bash", "-c", "echo ready"]}},
                                            "readiness": {
                                                "httpGet": {
                                                    "path": "/healthz",
                                                    "port": 80,
                                                    "httpHeaders": [
                                                        {"name": "Content-Type"},
                                                        {"value": "application/json"},
                                                    ],
                                                }
                                            },
                                            "startup": {
                                                "tcpSocket": {"port": 8000, "host": "app.host.com"},
                                                "initialDelaySeconds": 0,
                                                "timeoutSeconds": 1,
                                                "periodSeconds": 10,
                                                "successThreshold": 1,
                                                "failureThreshold": 3,
                                            },
                                        },
                                    }
                                ],
                                "hooks": {"preRelease": {"procCommand": "python manage.py migrate"}},
                                "svcDiscovery": {
                                    "bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user", "moduleName": "api"}]
                                },
                            },
                        },
                    ],
                },
                f"""specVersion: 3
appVersion: '1.0'
app:
  region: default
  bkAppCode: foo-app
  bkAppName: 默认应用名称
  market:
    category: 运维工具
    introduction: 应用简介
    description: 应用描述
    displayOptions:
      width: 800
      height: 600
      openMode: desktop
      isWinMaximize: false
      visible: true
modules:
  - name: frontend
    isDefault: true
    sourceDir: src/frontend
    language: NodeJS
    spec:
      addons:
        - name: mysql
        - name: rabbitmq
      configuration:
        env:
          - name: FOO
            value: value_of_foo
            description: 环境变量描述文件
          - name: FOO1
            value: ''
            description: 测试空值
      processes:
        - name: web
          procCommand: npm run server
          resQuotaPlan: 4C1G
          replicas: 2
          probes:
            liveness:
              exec:
                command:
                  - cat
            readiness:
              httpGet:
                path: /healthz
                port: 80
          services:
            - name: web
              protocol: TCP
              exposedType:
                name: bk/http
              targetPort: {settings.CONTAINER_PORT}
              port: 80
      hooks:
        preRelease:
          procCommand: bin/pre-release.sh
      svcDiscovery:
        bkSaaS:
          - bkAppCode: bk-iam
          - bkAppCode: bk-user
  - name: api_server
    isDefault: false
    sourceDir: src/backend
    language: Python
    spec:
      addons:
        - name: mysql
          shareFrom: default
        - name: rabbitmq
          shareFrom: default
      configuration:
        env:
          - name: FOO
            value: value_of_foo
            description: 环境变量描述文件
      processes:
        - name: server
          procCommand: python manage.py runserver
          resQuotaPlan: 4C1G
          replicas: 2
          probes:
            liveness:
              exec:
                command:
                  - /bin/bash
                  - -c
                  - echo ready
            readiness:
              httpGet:
                path: /healthz
                port: 80
                httpHeaders:
                  - name: Content-Type
                  - value: application/json
            startup:
              tcpSocket:
                port: 8000
                host: app.host.com
              initialDelaySeconds: 0
              timeoutSeconds: 1
              periodSeconds: 10
              successThreshold: 1
              failureThreshold: 3
      hooks:
        preRelease:
          procCommand: python manage.py migrate
      svcDiscovery:
        bkSaaS:
          - bkAppCode: bk-iam
          - bkAppCode: bk-user
            moduleName: api
""",
            ),
            # Test 2: one module in the first level
            (
                """spec_version: 2
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
module:
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
""",
                {
                    "specVersion": 3,
                    "appVersion": "1.0",
                    "app": {
                        "region": "default",
                        "bkAppCode": "foo-app",
                        "bkAppName": "默认应用名称",
                        "market": {
                            "category": "运维工具",
                            "introduction": "应用简介",
                            "description": "应用描述",
                            "displayOptions": {
                                "width": 800,
                                "height": 600,
                                "openMode": "desktop",
                                "isWinMaximize": False,
                                "visible": True,
                            },
                        },
                    },
                    "module": {
                        "name": "default",
                        "sourceDir": "src/frontend",
                        "language": "NodeJS",
                        "spec": {
                            "addons": [{"name": "mysql"}, {"name": "rabbitmq"}],
                            "configuration": {
                                "env": [{"name": "FOO", "value": "value_of_foo", "description": "环境变量描述文件"}]
                            },
                            "processes": [
                                {
                                    "name": "web",
                                    "procCommand": "npm run server",
                                    "resQuotaPlan": "4C1G",
                                    "replicas": 2,
                                    "probes": {
                                        "liveness": {"exec": {"command": ["cat"]}},
                                        "readiness": {"httpGet": {"path": "/healthz", "port": 80}},
                                    },
                                    "services": [
                                        {
                                            "name": "web",
                                            "protocol": "TCP",
                                            "targetPort": settings.CONTAINER_PORT,
                                            "port": 80,
                                            "exposedType": {"name": "bk/http"},
                                        }
                                    ],
                                }
                            ],
                            "hooks": {"preRelease": {"procCommand": "bin/pre-release.sh"}},
                            "svcDiscovery": {"bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user"}]},
                        },
                    },
                },
                f"""specVersion: 3
appVersion: '1.0'
app:
  region: default
  bkAppCode: foo-app
  bkAppName: 默认应用名称
  market:
    category: 运维工具
    introduction: 应用简介
    description: 应用描述
    displayOptions:
      width: 800
      height: 600
      openMode: desktop
      isWinMaximize: false
      visible: true
module:
  name: default
  sourceDir: src/frontend
  language: NodeJS
  spec:
    addons:
      - name: mysql
      - name: rabbitmq
    configuration:
      env:
        - name: FOO
          value: value_of_foo
          description: 环境变量描述文件
    processes:
      - name: web
        procCommand: npm run server
        resQuotaPlan: 4C1G
        replicas: 2
        probes:
          liveness:
            exec:
              command:
                - cat
          readiness:
            httpGet:
              path: /healthz
              port: 80
        services:
          - name: web
            protocol: TCP
            exposedType:
              name: bk/http
            targetPort: {settings.CONTAINER_PORT}
            port: 80
    hooks:
      preRelease:
        procCommand: bin/pre-release.sh
    svcDiscovery:
      bkSaaS:
        - bkAppCode: bk-iam
        - bkAppCode: bk-user
""",
            ),
            # Test 3: simple template without module.source_dir
            (
                """spec_version: 2
module:
  language: Python
  processes:
    web:
      command: gunicorn wsgi -w 4 -b [::]:${PORT}
    worker:
      command: celery -A app -l info
  bkmonitor:
    port: 5001
""",
                {
                    "specVersion": 3,
                    "module": {
                        "name": "default",
                        "language": "Python",
                        "spec": {
                            "processes": [
                                {
                                    "name": "web",
                                    "procCommand": "gunicorn wsgi -w 4 -b [::]:${PORT}",
                                    "services": [
                                        {
                                            "name": "web",
                                            "protocol": "TCP",
                                            "exposedType": {"name": "bk/http"},
                                            "targetPort": settings.CONTAINER_PORT,
                                            "port": 80,
                                        },
                                        {"name": "metrics", "protocol": "TCP", "port": 5001, "targetPort": 5001},
                                    ],
                                },
                                {
                                    "name": "worker",
                                    "procCommand": "celery -A app -l info",
                                },
                            ],
                            "observability": {
                                "monitoring": {
                                    "metrics": [{"process": "web", "serviceName": "metrics", "path": "/metrics"}]
                                }
                            },
                        },
                    },
                },
                f"""specVersion: 3
module:
  name: default
  language: Python
  spec:
    processes:
      - name: web
        procCommand: gunicorn wsgi -w 4 -b [::]:${{PORT}}
        services:
          - name: web
            protocol: TCP
            exposedType:
              name: bk/http
            targetPort: {settings.CONTAINER_PORT}
            port: 80
          - name: metrics
            protocol: TCP
            port: 5001
            targetPort: 5001
      - name: worker
        procCommand: celery -A app -l info
    observability:
      monitoring:
        metrics:
          - process: web
            serviceName: metrics
            path: /metrics
""",
            ),
        ],
    )
    def test_app_desc_transform(self, api_client, spec2_yaml, expected_spec3_data, expected_spec3_yaml):
        """测试应用描述文件转换接口"""
        response = api_client.post(
            reverse("api.tools.app_desc.transform"), data=spec2_yaml, content_type="application/yaml"
        )
        output_data = yaml.safe_load(response.content)
        assert output_data == expected_spec3_data

        output_yaml = response.content.decode(settings.DEFAULT_CHARSET)
        assert output_yaml == expected_spec3_yaml

    @pytest.mark.parametrize(
        ("spec2_yaml", "expected_exception_detail"),
        [
            (
                """modules:
                - name: default
                - name: web
                """,
                "modules: 期望是包含类目的字典，得到类型为 “list”。",
            ),
            (
                """    """,
                "No data provided",
            ),
            (
                """spec_version: 2""",
                "one of 'modules' or 'module' is required.",
            ),
            (
                """
module:
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
        readiness:
          http_get:
            path: /healthz
            port: 80
            http_headers:
              - name: Content-Type
                value: application/json
                """,
                "module.processes.web.probes.readiness.http_get.http_headers: Each item in http_headers must be one key: value pair.",
            ),
        ],
    )
    def test_app_desc_transform_exception(self, api_client, spec2_yaml, expected_exception_detail):
        response = api_client.post(
            reverse("api.tools.app_desc.transform"), data=spec2_yaml, content_type="application/yaml"
        )

        response_data = response.json()
        assert response_data["detail"] == expected_exception_detail
