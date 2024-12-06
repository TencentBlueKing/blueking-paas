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

from typing import Dict, List

from django.conf import settings

from .entities import IngressPathBackend, ServicePortPair

_dev_sandbox_ingress_service_conf = [
    # dev sandbox 中 devserver 的路径与端口映射
    {
        "path_prefix": "/devserver/",
        "service_port_name": "devserver",
        "port": 8000,
        "target_port": settings.DEV_SANDBOX_DEVSERVER_PORT,
    },
    # dev sandbox 中 saas 应用的路径与端口映射
    {"path_prefix": "/app/", "service_port_name": "app", "port": 80, "target_port": settings.CONTAINER_PORT},
]

DEV_SANDBOX_SVC_PORT_PAIRS: List[ServicePortPair] = [
    ServicePortPair(name=conf["service_port_name"], port=conf["port"], target_port=conf["target_port"])
    for conf in _dev_sandbox_ingress_service_conf
]

_code_editor_ingress_service_conf = [
    # code editor 的路径与端口映射
    {
        "path_prefix": "/code-editor/",
        "service_port_name": "code-editor",
        "port": 10251,
        "target_port": settings.CODE_EDITOR_PORT,
    },
]

CODE_EDITOR_SVC_PORT_PAIRS: List[ServicePortPair] = [
    ServicePortPair(name=conf["service_port_name"], port=conf["port"], target_port=conf["target_port"])
    for conf in _code_editor_ingress_service_conf
]


def get_ingress_path_backends(
    service_name: str, service_confs: List[Dict], dev_sandbox_code: str = ""
) -> List[IngressPathBackend]:
    """get ingress path backends from service_confs with service_name and dev_sandbox_code

    :param service_name: Service name
    :param dev_sandbox_code: dev sandbox code.
    :param service_confs: service configs
    """
    if not dev_sandbox_code:
        return [
            IngressPathBackend(
                path_prefix=conf["path_prefix"],
                service_name=service_name,
                service_port_name=conf["service_port_name"],
            )
            for conf in service_confs
        ]

    return [
        IngressPathBackend(
            path_prefix=f"/dev_sandbox/{dev_sandbox_code}{conf['path_prefix']}",
            service_name=service_name,
            service_port_name=conf["service_port_name"],
        )
        for conf in service_confs
    ]


def get_dev_sandbox_ingress_path_backends(service_name: str, dev_sandbox_code: str = "") -> List[IngressPathBackend]:
    return get_ingress_path_backends(service_name, _dev_sandbox_ingress_service_conf, dev_sandbox_code)


def get_code_editor_ingress_path_backends(service_name: str, dev_sandbox_code: str = "") -> List[IngressPathBackend]:
    return get_ingress_path_backends(service_name, _code_editor_ingress_service_conf, dev_sandbox_code)
