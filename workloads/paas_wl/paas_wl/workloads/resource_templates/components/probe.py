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
from typing import Optional

import cattr
from attrs import define
from django.conf import settings

from paas_wl.workloads.resource_templates.components.base import ExecAction, HTTPGetAction, TCPSocketAction


@define
class Probe:
    exec: Optional[ExecAction] = None
    failureThreshold: int = 3
    initialDelaySeconds: Optional[int] = None
    periodSeconds: int = 10
    successThreshold: int = 1
    # k8s 1.8 不支持该字段
    # terminationGracePeriodSeconds: Optional[int] = None
    timeoutSeconds: int = 1
    httpGet: Optional[HTTPGetAction] = None
    tcpSocket: Optional[TCPSocketAction] = None


default_readiness_probe = cattr.structure(
    {
        'tcpSocket': {'port': settings.CONTAINER_PORT},
        'initialDelaySeconds': 1,
        'periodSeconds': 15,
        'failureThreshold': 6,
    },
    Probe,
)
