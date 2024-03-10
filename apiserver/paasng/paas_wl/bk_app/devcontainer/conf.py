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
from typing import List

from django.conf import settings

from .entities import IngressPathBackend, ServicePortPair

INGRESS_SERVICE_CONF = [
    # devcontainer 中 devserver 的路径与端口映射
    {
        "path_prefix": "devcontainer/",
        "service_port_name": "devserver",
        "port": 8000,
        "target_port": settings.DEVSERVER_PORT,
    },
    # devcontainer 中 saas 应用的路径与端口映射
    {"path_prefix": "/", "service_port_name": "app", "port": 80, "target_port": settings.CONTAINER_PORT},
]


DEVCONTAINER_SVC_PORT_PAIRS: List[ServicePortPair] = [
    ServicePortPair(name=conf["service_port_name"], port=conf["port"], target_port=conf["target_port"])
    for conf in INGRESS_SERVICE_CONF
]


def get_ingress_path_backends(service_name: str) -> List[IngressPathBackend]:
    """get ingress path backends from INGRESS_SERVICE_CONF with service_name"""
    return [
        IngressPathBackend(
            path_prefix=conf["path_prefix"],
            service_name=service_name,
            service_port_name=conf["service_port_name"],
        )
        for conf in INGRESS_SERVICE_CONF
    ]
