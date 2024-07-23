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

"""Resource Definition of `BkApplication` kind.

Use `pydantic` to get good JSON-Schema support, which is essential for CRD.
"""
import datetime
import shlex
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator

from paas_wl.bk_app.cnative.specs.constants import ApiVersion, MResPhaseType, ResQuotaPlan
from paas_wl.workloads.networking.constants import ExposedTypeName
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.utils.procfile import generate_bash_command_with_tokens
from paasng.utils.structure import register

from .metadata import ObjectMetadata


class MetaV1Condition(BaseModel):
    """Condition contains details for one aspect of the current state of this API Resource"""

    type: str
    status: Literal["True", "False", "Unknown"] = "Unknown"
    reason: str
    message: str
    observedGeneration: int = Field(default=0)


class AutoscalingSpec(BaseModel):
    """Autoscaling specification"""

    minReplicas: int
    maxReplicas: int
    policy: str = Field(..., min_length=1)


class ExecAction(BaseModel):
    """ExecAction describes a "run in container" action."""

    command: List[str]


class HTTPHeader(BaseModel):
    """HTTPHeader describes a custom header to be used in HTTP probes"""

    name: str
    value: str


class HTTPGetAction(BaseModel):
    """HTTPGetAction describes an action based on HTTP Get requests."""

    port: Union[int, str]
    host: Optional[str] = None
    path: Optional[str] = None
    httpHeaders: List[HTTPHeader] = Field(default_factory=list)
    scheme: Optional[Literal["HTTP", "HTTPS"]] = "HTTP"


class TCPSocketAction(BaseModel):
    """TCPSocketAction describes an action based on opening a socket"""

    port: Union[int, str]
    host: Optional[str] = None


class Probe(BaseModel):
    """Resource: Probe

    :param exec:命令行探活检测机制
    :param httpGet:http 请求探活检测机制
    :param tcpSocket:tcp 请求探活检测机制

    :param initialDelaySeconds: 容器启动后等待时间
    :param timeoutSeconds: 探针执行超时时间
    :param periodSeconds: 探针执行间隔时间
    :param successThreshold: 连续几次检测成功后，判定容器是健康的
    :param failureThreshold: 连续几次检测失败后，判定容器是不健康
    """

    exec: Optional[ExecAction] = None
    httpGet: Optional[HTTPGetAction] = None
    tcpSocket: Optional[TCPSocketAction] = None

    initialDelaySeconds: Optional[int] = 0
    timeoutSeconds: Optional[int] = 1
    periodSeconds: Optional[int] = 10
    successThreshold: Optional[int] = 1
    failureThreshold: Optional[int] = 3

    def to_snake_case(self) -> Dict[str, Any]:
        """将探针字段转换成下划线格式"""
        exec_handler, http_get_handler, tcp_socket_handler = None, None, None
        if self.exec:
            exec_handler = {"command": self.exec.command}
        elif self.httpGet:
            http_get_handler = {
                "path": self.httpGet.path,
                "port": self.httpGet.port,
                "http_headers": [{"name": h.name, "value": h.value} for h in self.httpGet.httpHeaders],
                "host": self.httpGet.host,
                "scheme": self.httpGet.scheme,
            }
        elif self.tcpSocket:
            tcp_socket_handler = {"port": self.tcpSocket.port, "host": self.tcpSocket.host}

        return {
            "exec": exec_handler,
            "http_get": http_get_handler,
            "tcp_socket": tcp_socket_handler,
            "initial_delay_seconds": self.initialDelaySeconds,
            "timeout_seconds": self.timeoutSeconds,
            "period_seconds": self.periodSeconds,
            "success_threshold": self.successThreshold,
            "failure_threshold": self.failureThreshold,
        }


class ProbeSet(BaseModel):
    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None

    def to_snake_case(self) -> Dict[str, Any]:
        """将探针字段转换成下划线格式"""
        return {
            "liveness": self.liveness.to_snake_case() if self.liveness else None,
            "readiness": self.readiness.to_snake_case() if self.readiness else None,
            "startup": self.startup.to_snake_case() if self.startup else None,
        }


class ExposedType(BaseModel):
    """ExposedType is the exposed type of the ProcService

    :param name: the name of the exposed type
    """

    name: Literal[ExposedTypeName.BK_HTTP] = ExposedTypeName.BK_HTTP


class ProcService(BaseModel):
    """ProcService is a process service which used to expose network

    :param name: the name of the service
    :param targetPort: the target port of the service
    :param protocol: the protocol of the service
    :param exposedType: the exposed type of the service. If not specified, the service can only
        be accessed within the cluster, not from outside.
    :param port: the port that will be exposed by this service. If not specified, the value of
        the 'targetPort' field is used.
    """

    name: str
    targetPort: int
    protocol: Literal["TCP", "UDP"] = "TCP"
    exposedType: Optional[ExposedType] = None
    port: Optional[int] = None

    def __init__(self, **data):
        if not data.get("port"):
            data["port"] = data["targetPort"]
        super().__init__(**data)

    def to_snake_case(self) -> Dict[str, Any]:
        exposed_type = None
        if self.exposedType:
            exposed_type = {"name": self.exposedType.name}

        return {
            "name": self.name,
            "target_port": self.targetPort,
            "protocol": self.protocol,
            "exposed_type": exposed_type,
            "port": self.port,
        }


class BkAppProcess(BaseModel):
    """Process resource"""

    name: str
    replicas: int = 1
    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    targetPort: Optional[int] = None
    resQuotaPlan: Optional[ResQuotaPlan] = None
    autoscaling: Optional[AutoscalingSpec] = None
    probes: Optional[ProbeSet] = None
    services: Optional[List[ProcService]] = None

    # proc_command 用于向后兼容普通应用部署场景(shlex.split + shlex.join 难以保证正确性)
    proc_command: Optional[str] = Field(None)

    def __init__(self, **data):
        # 处理 specVersion: 3 中驼峰传递 procCommand
        # TODO 先采用 paasng.platform.declarative.deployment.validations.v2.DeploymentDescSLZ 中的做法, 后续统一优化
        if proc_command := data.get("procCommand"):
            data["proc_command"] = proc_command
            data["command"] = None
            data["args"] = shlex.split(proc_command)
        super().__init__(**data)

    def get_proc_command(self) -> str:
        """get_proc_command: 生成 Procfile 文件中对应的命令行"""
        if self.proc_command:
            return self.proc_command
        return generate_bash_command_with_tokens(self.command or [], self.args or [])

    @validator("services")
    def validate_services(cls, services):  # noqa: N805
        """validate services. it checks whether names, targetPort and ports are duplicated"""
        if not services:
            return services

        names = set()
        target_ports = set()
        ports = set()

        for svc in services:
            if svc.name in names:
                raise ValueError(f"duplicate service name: {svc.name}")
            names.add(svc.name)

            if svc.targetPort in target_ports:
                raise ValueError(f"duplicate target port: {svc.targetPort}")
            target_ports.add(svc.targetPort)

            if svc.port and svc.port in ports:
                raise ValueError(f"duplicate port: {svc.port}")
            ports.add(svc.port)

        return services


class Hook(BaseModel):
    """A hook object"""

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)

    def __init__(self, **data):
        # TODO 先采用 paasng.platform.declarative.deployment.validations.v2.DeploymentDescSLZ 中的做法, 后续统一优化
        if proc_command := data.get("procCommand"):
            data["command"] = None
            data["args"] = shlex.split(proc_command)
        super().__init__(**data)


class BkAppHooks(BaseModel):
    """Hook commands for BkApp"""

    preRelease: Optional[Hook] = None


class EnvVar(BaseModel):
    """Environment variable key-value pair"""

    name: str
    value: str


class BkAppConfiguration(BaseModel):
    """Configuration for BkApp"""

    env: List[EnvVar] = Field(default_factory=list)


@register
class ConfigMapSource(BaseModel):
    name: str


@register
class PersistentStorage(BaseModel):
    name: str


@register
class VolumeSource(BaseModel):
    configMap: Optional[ConfigMapSource] = None
    persistentStorage: Optional[PersistentStorage] = None


class Mount(BaseModel):
    mountPath: str
    name: str
    source: VolumeSource


class MountOverlay(BaseModel):
    envName: str
    mountPath: str
    name: str
    source: VolumeSource


class ReplicasOverlay(BaseModel):
    """Overwrite process's replicas by environment"""

    envName: str
    process: str
    count: int


class ResQuotaOverlay(BaseModel):
    """Overwrite process's resQuota by environment"""

    envName: str
    process: str
    plan: str


class EnvVarOverlay(BaseModel):
    """Overwrite or add application's environment vars by environment"""

    envName: str
    name: str
    value: str


class AutoscalingOverlay(BaseModel):
    """Overwrite or add application's autoscaling by environment"""

    envName: str
    process: str
    minReplicas: int
    maxReplicas: int
    policy: str = Field(..., min_length=1)


class EnvOverlay(BaseModel):
    """Defines environment specified configs"""

    replicas: Optional[List[ReplicasOverlay]] = None
    resQuotas: Optional[List[ResQuotaOverlay]] = None
    envVariables: Optional[List[EnvVarOverlay]] = None
    autoscaling: Optional[List[AutoscalingOverlay]] = None
    mounts: Optional[List[MountOverlay]] = None

    def append_item(self, field_name: str, item: Any):
        """A shortcut method that append an item to the given field."""
        assert field_name in {
            "replicas",
            "resQuotas",
            "envVariables",
            "autoscaling",
            "mounts",
        }, f"{field_name} invalid"

        if getattr(self, field_name) is None:
            setattr(self, field_name, [])
        getattr(self, field_name).append(item)


class BkAppBuildConfig(BaseModel):
    """BuildConfig for BkApp"""

    # 兼容使用注解支持多镜像的场景（v1alpha1 遗留功能）
    image: Optional[str] = None
    imagePullPolicy: str = ImagePullPolicy.IF_NOT_PRESENT.value
    imageCredentialsName: Optional[str] = None
    dockerfile: Optional[str] = None
    buildTarget: Optional[str] = None
    args: Optional[Dict[str, str]] = None


class BkAppAddonSpec(BaseModel):
    """AddonSpec for BkApp"""

    name: str
    value: str


class BkAppAddon(BaseModel):
    """Addon for BkApp

    :param name: The name of the addon.
    :param specs: The specs of the addon.
    :param sharedFromModule: The module name the addon is shared from.
    """

    name: str
    specs: List[BkAppAddonSpec] = Field(default_factory=list)
    sharedFromModule: Optional[str] = None


@register
class HostAlias(BaseModel):
    """A host alias entry"""

    ip: str
    hostnames: List[str]

    def __hash__(self):
        return hash((self.ip, tuple(sorted(self.hostnames))))

    def __eq__(self, other):
        if isinstance(other, HostAlias):
            return self.ip == other.ip and sorted(self.hostnames) == sorted(other.hostnames)
        return False


@register
class DomainResolution(BaseModel):
    """Domain resolution config"""

    nameservers: List[str] = Field(default_factory=list)
    hostAliases: List[HostAlias] = Field(default_factory=list)


@register
class SvcDiscEntryBkSaaS(BaseModel):
    """A service discovery entry that represents an application and an optional module."""

    bkAppCode: str
    moduleName: Optional[str] = None

    def __hash__(self):
        return hash((self.bkAppCode, self.moduleName))

    def __eq__(self, other):
        if isinstance(other, SvcDiscEntryBkSaaS):
            return self.bkAppCode == other.bkAppCode and self.moduleName == other.moduleName
        return False


class SvcDiscConfig(BaseModel):
    """Service discovery config"""

    bkSaaS: List[SvcDiscEntryBkSaaS] = Field(default_factory=list)


class BkAppSpec(BaseModel):
    """Spec of BkApp resource"""

    build: Optional[BkAppBuildConfig] = None
    processes: List[BkAppProcess] = Field(default_factory=list)
    hooks: Optional[BkAppHooks] = None
    addons: List[BkAppAddon] = Field(default_factory=list)
    mounts: Optional[List[Mount]] = None
    configuration: BkAppConfiguration = Field(default_factory=BkAppConfiguration)
    domainResolution: Optional[DomainResolution] = None
    svcDiscovery: Optional[SvcDiscConfig] = None
    envOverlay: Optional[EnvOverlay] = None

    @validator("processes")
    def validate_processes(cls, processes):  # noqa: N805
        """validate processes.
        - check whether exposed types are duplicated. 一个 BkApp 只能有一个 bk/http 类型的暴露服务作为主入口
        """
        if not processes:
            return processes

        exposed_types = set()

        for proc in processes:
            if not proc.services:
                continue

            for svc in proc.services:
                if not svc.exposedType:
                    continue

                if svc.exposedType.name in exposed_types:
                    raise ValueError(f"exposed type {svc.exposedType.name} is duplicated in one app module")

                exposed_types.add(svc.exposedType.name)

        return processes


class BkAppStatus(BaseModel):
    """BkAppStatus defines the observed state of BkApp"""

    phase: str = MResPhaseType.AppPending.value
    observedGeneration: int = Field(default=0)
    conditions: List[MetaV1Condition] = Field(default_factory=list)
    lastUpdate: Optional[datetime.datetime]
    deployId: str = ""


class BkAppResource(BaseModel):
    """Blueking Application resource"""

    apiVersion: str = ApiVersion.V1ALPHA2.value
    kind: Literal["BkApp"] = "BkApp"
    metadata: ObjectMetadata
    spec: BkAppSpec
    status: BkAppStatus = Field(default_factory=BkAppStatus)

    @validator("apiVersion")
    def validate_api_version(cls, v) -> str:  # noqa: N805
        """ApiVersion can not be used for "Literal" validation directly, so we define a
        custom validator instead.
        """
        if v != ApiVersion.V1ALPHA2:
            raise ValueError(f"{v} is not valid, use {ApiVersion.V1ALPHA2}")
        return v

    def to_deployable(self) -> Dict:
        """Return the deployable manifest, some fields are excluded."""
        # Set `exclude_none` to remove all fields whose value is `None` because
        # entries such as `"hooks": null` is not processable in Kubernetes 1.18.
        result = self.dict(exclude_none=True, exclude={"status"})
        result["metadata"].pop("generation", None)
        return result
