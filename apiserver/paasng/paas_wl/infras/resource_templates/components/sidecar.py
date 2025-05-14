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

from typing import Dict, List, Optional

from attrs import define

from paas_wl.infras.resource_templates.components.base import ExecAction, HTTPGetAction, TCPSocketAction
from paas_wl.infras.resource_templates.components.probe import Probe
from paas_wl.infras.resource_templates.components.volume import VolumeMount


@define
class ConfigMapEnvSource:
    name: Optional[str] = None
    optional: bool = False


@define
class SecretEnvSource:
    name: Optional[str] = None
    optional: bool = False


@define
class EnvFromSource:
    configMapRef: Optional[ConfigMapEnvSource] = None
    prefix: Optional[str] = None
    secretRef: Optional[SecretEnvSource] = None


@define
class EnvVar:
    name: str
    value: str


@define
class ContainerPort:
    containerPort: int
    hostIP: Optional[str] = None
    hostPort: Optional[int] = None
    name: Optional[str] = None
    protocol: Optional[str] = None


@define
class LifecycleHandler:
    exec: Optional[ExecAction] = None
    httpGet: Optional[HTTPGetAction] = None
    tcpSocket: Optional[TCPSocketAction] = None


@define
class Lifecycle:
    postStart: Optional[LifecycleHandler] = None
    preStop: Optional[LifecycleHandler] = None


@define
class VolumeDevice:
    devicePath: str
    name: str


@define
class ResourceRequirements:
    limits: Optional[Dict[str, str]] = None
    requests: Optional[Dict[str, str]] = None


@define
class SecurityContext:
    privileged: bool = False


@define
class Container:
    name: str
    image: str
    imagePullPolicy: Optional[str] = None
    args: Optional[List[str]] = None
    command: Optional[List[str]] = None
    env: Optional[List[EnvVar]] = None
    envFrom: Optional[List[EnvFromSource]] = None
    ports: Optional[List[ContainerPort]] = None
    lifecycle: Optional[Lifecycle] = None
    resources: Optional[ResourceRequirements] = None
    securityContext: Optional[SecurityContext] = None
    livenessProbe: Optional[Probe] = None
    readinessProbe: Optional[Probe] = None
    startupProbe: Optional[Probe] = None
    volumeDevices: Optional[List[VolumeDevice]] = None
    volumeMounts: Optional[List[VolumeMount]] = None
    workingDir: Optional[str] = None
