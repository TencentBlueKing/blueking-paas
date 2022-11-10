# -*- coding: utf-8 -*-
from typing import Dict, List, Optional

from attrs import define

from paas_wl.workloads.resource_templates.components.base import ExecAction, HTTPGetAction, TCPSocketAction
from paas_wl.workloads.resource_templates.components.probe import Probe
from paas_wl.workloads.resource_templates.components.volume import VolumeMount


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
