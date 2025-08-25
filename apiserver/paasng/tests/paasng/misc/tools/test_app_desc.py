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

from collections import OrderedDict
from typing import Any

import pytest
from django.conf import settings

from paasng.misc.tools.app_desc.app_desc import (
    transform_app_desc_spec2_to_spec3,
    transform_module_spec,
    transform_modules_section,
)


@pytest.mark.parametrize(
    ("spec_input", "expected_spec_output"),
    [
        # Test 1: Transform services to addons
        (
            {"services": [{"name": "mysql"}, {"name": "rabbitmq"}]},
            OrderedDict({"addons": [{"name": "mysql"}, {"name": "rabbitmq"}]}),
        ),
        # Test 2: Transform env_variables to configuration.env
        (
            {
                "env_variables": [
                    {"key": "FOO", "value": "value_of_foo", "description": "环境变量"},
                    {"key": "BAR", "value": "value_of_bar", "description": "另一个环境变量"},
                ]
            },
            OrderedDict(
                {
                    "configuration": {
                        "env": [
                            {"name": "FOO", "value": "value_of_foo", "description": "环境变量"},
                            {"name": "BAR", "value": "value_of_bar", "description": "另一个环境变量"},
                        ]
                    }
                }
            ),
        ),
        # Test 3: Transform processes (including probes)
        (
            {
                "processes": {
                    "web": {
                        "command": "npm run server",
                        "plan": "4C1G5R",
                        "replicas": 2,
                        "probes": {
                            "liveness": {"exec": {"command": ["cat"]}},
                            "readiness": {"http_get": {"path": "/healthz", "port": 80}},
                        },
                    },
                    "worker": {
                        "command": "python manage.py runserver",
                        "plan": "4C1G5R",
                        "replicas": 2,
                        "probes": {
                            "liveness": {"exec": {"command": ["/bin/bash", "-c", "echo ready"]}},
                            "readiness": {"http_get": {"path": "/healthz", "port": 80}},
                        },
                    },
                }
            },
            OrderedDict(
                {
                    "processes": [
                        OrderedDict(
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
                        ),
                        OrderedDict(
                            {
                                "name": "worker",
                                "procCommand": "python manage.py runserver",
                                "resQuotaPlan": "4C1G",
                                "replicas": 2,
                                "probes": {
                                    "liveness": {"exec": {"command": ["/bin/bash", "-c", "echo ready"]}},
                                    "readiness": {"httpGet": {"path": "/healthz", "port": 80}},
                                },
                            }
                        ),
                    ]
                }
            ),
        ),
        # Test 4: Transform scripts (preRelease hook)
        (
            {"scripts": {"pre_release_hook": "bin/pre-release.sh"}},
            OrderedDict({"hooks": {"preRelease": {"procCommand": "bin/pre-release.sh"}}}),
        ),
        # Test 5: Transform svc_discovery (bk_saas)
        (
            {
                "svc_discovery": {
                    "bk_saas": [{"bk_app_code": "bk-iam"}, {"bk_app_code": "bk-user", "module_name": "api"}]
                }
            },
            OrderedDict(
                {"svcDiscovery": {"bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user", "moduleName": "api"}]}}
            ),
        ),
    ],
)
def test_transform_module_spec(spec_input, expected_spec_output):
    spec: OrderedDict[str, Any] = OrderedDict()

    # Simulate the transformation of different module specs
    for key, value in spec_input.items():
        transform_module_spec(spec, key, value)

    # Assert if the result matches the expected output
    assert spec == expected_spec_output


@pytest.mark.parametrize(
    ("modules_data", "expected_modules_data"),
    [
        # Test 1: Test two modules
        (
            {
                "default": {
                    "is_default": True,
                    "source_dir": "src/server",
                    "language": "Python",
                    "services": [{"name": "mysql"}, {"name": "rabbitmq"}],
                    "env_variables": [{"key": "FOO", "value": "value_of_foo", "description": "环境变量"}],
                },
                "frontend": {
                    "is_default": False,
                    "source_dir": "src/frontend",
                    "language": "NodeJS",
                    "services": [{"name": "mysql"}, {"name": "rabbitmq"}],
                    "env_variables": [
                        {"key": "FOO", "value": "value_of_foo", "description": "环境变量"},
                        {"key": "BAR", "value": "value_of_bar", "description": "另一个环境变量"},
                    ],
                    "processes": {
                        "web": {
                            "command": "npm run server",
                            "plan": "4C1G5R",
                            "replicas": 2,
                            "probes": {
                                "liveness": {"exec": {"command": ["cat"]}},
                                "readiness": {"http_get": {"path": "/healthz", "port": 80}},
                            },
                        }
                    },
                },
            },
            [
                OrderedDict(
                    {
                        "name": "default",
                        "isDefault": True,
                        "sourceDir": "src/server",
                        "language": "Python",
                        "spec": OrderedDict(
                            {
                                "addons": [{"name": "mysql"}, {"name": "rabbitmq"}],
                                "configuration": {
                                    "env": [{"name": "FOO", "value": "value_of_foo", "description": "环境变量"}]
                                },
                            }
                        ),
                    }
                ),
                OrderedDict(
                    {
                        "name": "frontend",
                        "isDefault": False,
                        "sourceDir": "src/frontend",
                        "language": "NodeJS",
                        "spec": OrderedDict(
                            {
                                "addons": [{"name": "mysql"}, {"name": "rabbitmq"}],
                                "configuration": {
                                    "env": [
                                        {"name": "FOO", "value": "value_of_foo", "description": "环境变量"},
                                        {"name": "BAR", "value": "value_of_bar", "description": "另一个环境变量"},
                                    ]
                                },
                                "processes": [
                                    OrderedDict(
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
                                    )
                                ],
                            }
                        ),
                    }
                ),
            ],
        ),
        # Test 2: Test one module with 5 types of specs
        (
            {
                "api_server": {
                    "is_default": False,
                    "source_dir": "src/backend",
                    "language": "Python",
                    "services": [
                        {"name": "mysql", "share_from": "default"},
                        {"name": "rabbitmq", "share_from": "default"},
                    ],
                    "env_variables": [{"key": "API_KEY", "value": "api_value", "description": "API 密钥"}],
                    "processes": {
                        "worker": {
                            "command": "python manage.py runserver",
                            "plan": "4C1G5R",
                            "replicas": 2,
                            "probes": {
                                "liveness": {"exec": {"command": ["/bin/bash", "-c", "echo ready"]}},
                                "readiness": {"http_get": {"path": "/healthz", "port": 80}},
                            },
                        }
                    },
                    "scripts": {"pre_release_hook": "python manage.py migrate"},
                    "svc_discovery": {
                        "bk_saas": [{"bk_app_code": "bk-iam"}, {"bk_app_code": "bk-user", "module_name": "api"}]
                    },
                }
            },
            [
                OrderedDict(
                    {
                        "name": "api_server",
                        "isDefault": False,
                        "sourceDir": "src/backend",
                        "language": "Python",
                        "spec": OrderedDict(
                            {
                                "addons": [
                                    {"name": "mysql", "shareFrom": "default"},
                                    {"name": "rabbitmq", "shareFrom": "default"},
                                ],
                                "configuration": {
                                    "env": [{"name": "API_KEY", "value": "api_value", "description": "API 密钥"}]
                                },
                                "processes": [
                                    OrderedDict(
                                        {
                                            "name": "worker",
                                            "procCommand": "python manage.py runserver",
                                            "resQuotaPlan": "4C1G",
                                            "replicas": 2,
                                            "probes": {
                                                "liveness": {"exec": {"command": ["/bin/bash", "-c", "echo ready"]}},
                                                "readiness": {"httpGet": {"path": "/healthz", "port": 80}},
                                            },
                                        }
                                    )
                                ],
                                "hooks": {"preRelease": {"procCommand": "python manage.py migrate"}},
                                "svcDiscovery": {
                                    "bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user", "moduleName": "api"}]
                                },
                            }
                        ),
                    }
                )
            ],
        ),
    ],
)
def test_transform_modules_section(modules_data, expected_modules_data):
    transformed_modules_data = transform_modules_section(modules_data)

    assert transformed_modules_data == expected_modules_data


@pytest.mark.parametrize(
    ("spec2_data", "expected_spec3_data"),
    [
        (
            {
                "spec_version": 2,
                "app_version": "1.0",
                "app": {
                    "region": "default",
                    "bk_app_code": "foo-app",
                    "bk_app_name": "默认应用名称",
                    "market": {
                        "category": "运维工具",
                        "introduction": "应用简介",
                        "description": "应用描述",
                        "display_options": {
                            "width": 800,
                            "height": 600,
                            "open_mode": "desktop",
                            "is_win_maximize": False,
                            "visible": True,
                        },
                    },
                },
                "module": {
                    "source_dir": "src/frontend",
                    "language": "NodeJS",
                    "services": [{"name": "mysql"}, {"name": "rabbitmq"}],
                    "env_variables": [
                        {"key": "FOO", "value": "value_of_foo", "description": "环境变量"},
                        {"key": "Baa", "value": "value_of_baa", "description": "环境变量"},
                    ],
                    "processes": {
                        "web": {
                            "command": "npm run server",
                            "plan": "4C1G5R",
                            "replicas": 2,
                            "probes": {
                                "liveness": {"exec": {"command": ["cat"]}},
                                "readiness": {"http_get": {"path": "/healthz", "port": 80}},
                            },
                        }
                    },
                    "scripts": {"pre_release_hook": "bin/pre-release.sh"},
                    "svc_discovery": {"bk_saas": ["bk-iam", "bk-user"]},
                },
            },
            OrderedDict(
                {
                    "specVersion": 3,
                    "appVersion": "1.0",
                    "app": OrderedDict(
                        {
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
                        }
                    ),
                    "module": OrderedDict(
                        {
                            "name": "default",
                            "sourceDir": "src/frontend",
                            "language": "NodeJS",
                            "spec": OrderedDict(
                                {
                                    "addons": [{"name": "mysql"}, {"name": "rabbitmq"}],
                                    "configuration": {
                                        "env": [
                                            {"name": "FOO", "value": "value_of_foo", "description": "环境变量"},
                                            {"name": "Baa", "value": "value_of_baa", "description": "环境变量"},
                                        ]
                                    },
                                    "processes": [
                                        OrderedDict(
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
                                        )
                                    ],
                                    "hooks": {"preRelease": {"procCommand": "bin/pre-release.sh"}},
                                    "svcDiscovery": {"bkSaaS": [{"bkAppCode": "bk-iam"}, {"bkAppCode": "bk-user"}]},
                                }
                            ),
                        }
                    ),
                }
            ),
        )
    ],
)
def test_transform_app_desc_spec2_to_spec3(spec2_data, expected_spec3_data):
    transformed_spec3_data = transform_app_desc_spec2_to_spec3(spec2_data)

    assert transformed_spec3_data == expected_spec3_data
