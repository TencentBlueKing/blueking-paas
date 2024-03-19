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
"""Resource Definition of `BkApplication` kind.

Use `pydantic` to get good JSON-Schema support, which is essential for CRD.
"""
import datetime
import shlex
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator

from paas_wl.bk_app.cnative.specs.apis import ObjectMetadata
from paas_wl.bk_app.cnative.specs.constants import ApiVersion, MResPhaseType, ResQuotaPlan
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.utils.structure import register


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

    port: Union[str, int]
    host: Optional[str] = None
    path: Optional[str] = None
    httpHeaders: List[HTTPHeader] = Field(default_factory=list)
    scheme: Optional[Literal["HTTP", "HTTPS"]] = None


class TCPSocketAction(BaseModel):
    """TCPSocketAction describes an action based on opening a socket"""

    port: Union[str, int]
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


class ProbeSet(BaseModel):
    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None


class BkAppProcess(BaseModel):
    """Process resource"""

    name: str
    replicas: int = 1
    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    targetPort: Optional[int] = None
    resQuotaPlan: Optional[ResQuotaPlan] = None
    autoscaling: Optional[AutoscalingSpec] = None

    # TODO: `probes` is NOT supported by operator now.
    probes: Optional[ProbeSet] = None

    # Deprecated: use resQuotaPlan instead in v1alpha2
    cpu: Optional[str] = None
    # Deprecated: use resQuotaPlan instead in v1alpha2
    memory: Optional[str] = None
    # Deprecated: use spec.build.image instead in v1alpha2
    image: Optional[str] = None
    # Deprecated: use spec.build.imagePullPolicy instead in v1alpha2
    imagePullPolicy: Optional[str] = None
    # proc_command 用于向后兼容普通应用部署场景(shlex.split + shlex.join 难以保证正确性)
    proc_command: Optional[str] = Field(None)

    def get_proc_command(self) -> str:
        """get_proc_command: Procfile 风格的命令
        使用场景:
        - buildpacks 构建方案使用该方法生成 Procfile 文件
        """
        if self.proc_command:
            return self.proc_command
        # Warning: 已知 shlex.join 不支持环境变量, 对于 buildpack 构建的应用, 使用 app_desc v3 描述文件, 有可能出现无法正常运行的问题
        # 例如会报错: Error: '${PORT:-5000}' is not a valid port number.
        return self._sanitize_proc_command(
            (shlex.join(self.command or []) + " " + shlex.join(self.args or [])).strip()
        )

    @staticmethod
    def _sanitize_proc_command(proc_command: str) -> str:
        """Sanitize the command and arg list, replace some special expressions which can't
        be interpreted by the operator.
        """
        # '${PORT:-5000}' is massively used by the app framework, while it can not work well with shlex.join,
        # here remove the single quote added by shlex.join.
        known_cases = [
            ("':$PORT'", ":$PORT"),
            ("':${PORT:-5000}'", ":${PORT}"),
            ("'[::]:${PORT}'", "[::]:${PORT}"),
            ("'[::]:${PORT:-5000}'", "[::]:${PORT}"),
        ]
        for old, new in known_cases:
            proc_command = proc_command.replace(old, new)
        return proc_command


class Hook(BaseModel):
    """A hook object"""

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)


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
    imagePullPolicy: str = ImagePullPolicy.IF_NOT_PRESENT
    imageCredentialsName: Optional[str] = None
    dockerfile: Optional[str] = None
    buildTarget: Optional[str] = None
    args: Optional[Dict[str, str]] = None


class BkAppAddonSpec(BaseModel):
    """AddonSpec for BkApp"""

    name: str
    value: str


class BkAppAddon(BaseModel):
    """Addon for BkApp"""

    name: str
    specs: List[BkAppAddonSpec] = Field(default_factory=list)
    sharedFrom: Optional[str] = None


@register
class HostAlias(BaseModel):
    """A host alias entry"""

    ip: str
    hostnames: List[str]


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


class BkAppStatus(BaseModel):
    """BkAppStatus defines the observed state of BkApp"""

    phase: str = MResPhaseType.AppPending
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
        if v not in [ApiVersion.V1ALPHA2, ApiVersion.V1ALPHA1]:
            raise ValueError(f"{v} is not valid, use {ApiVersion.V1ALPHA2} or {ApiVersion.V1ALPHA1}")
        return v

    def to_deployable(self) -> Dict:
        """Return the deployable manifest, some fields are excluded."""
        # Set `exclude_none` to remove all fields whose value is `None` because
        # entries such as `"hooks": null` is not processable in Kubernetes 1.18.
        result = self.dict(exclude_none=True, exclude={"status"})
        result["metadata"].pop("generation", None)
        return result
