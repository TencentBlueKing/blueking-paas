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

import shlex
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from paasng.platform.bkapp_model.constants import ImagePullPolicy, ResQuotaPlan
from paasng.utils.procfile import generate_bash_command_with_tokens
from paasng.utils.structure import register


class ConfigMapSource(BaseModel):
    name: str


class PersistentStorage(BaseModel):
    name: str


class VolumeSource(BaseModel):
    config_map: Optional[ConfigMapSource] = None
    persistent_storage: Optional[PersistentStorage] = None


class Mount(BaseModel):
    mount_path: str
    name: str
    source: VolumeSource


class MountOverlay(BaseModel):
    env_name: str
    mount_path: str
    name: str
    source: VolumeSource


@register
class SvcDiscEntryBkSaaS(BaseModel):
    """A service discovery entry that represents an application and an optional module."""

    bk_app_code: str
    module_name: Optional[str] = None

    def __init__(self, **data):
        # db 旧数据使用了 camel case
        if bk_app_code := data.get("bkAppCode"):
            data["bk_app_code"] = bk_app_code

        if module_name := data.get("moduleName"):
            data["module_name"] = module_name

        super().__init__(**data)

    def __hash__(self):
        return hash((self.bk_app_code, self.module_name))

    def __eq__(self, other):
        if isinstance(other, SvcDiscEntryBkSaaS):
            return self.bk_app_code == other.bk_app_code and self.module_name == other.module_name
        return False


class SvcDiscConfig(BaseModel):
    """Service discovery config"""

    bk_saas: List[SvcDiscEntryBkSaaS] = Field(default_factory=list)


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


class DomainResolution(BaseModel):
    """Domain resolution config"""

    nameservers: List[str] = Field(default_factory=list)
    host_aliases: List[HostAlias] = Field(default_factory=list)


class ResQuotaOverlay(BaseModel):
    env_name: str
    process: str
    plan: str


class ReplicasOverlay(BaseModel):
    env_name: str
    process: str
    count: int


class AutoscalingOverlay(BaseModel):
    env_name: str
    process: str
    min_replicas: int
    max_replicas: int
    policy: str = Field(..., min_length=1)


@register
class AutoscalingConfig(BaseModel):
    # 最小副本数量
    min_replicas: int
    # 最大副本数量
    max_replicas: int
    # 扩缩容策略
    policy: str


class ProcEnvOverlay(BaseModel):
    env_name: str
    plan_name: Optional[str] = None
    target_replicas: Optional[int] = None
    autoscaling: bool = False
    scaling_config: Optional[AutoscalingConfig] = None

    def __init__(self, **data):
        if env_name := data.get("environment_name"):
            data["env_name"] = env_name
        super().__init__(**data)


class EnvVar(BaseModel):
    """Environment variable key-value pair"""

    name: str
    value: str


class EnvVarOverlay(BaseModel):
    """Overwrite or add application's environment vars by environment"""

    env_name: str
    name: str
    value: str


class AppBuildConfig(BaseModel):
    image: Optional[str] = None
    image_pull_policy: str = ImagePullPolicy.IF_NOT_PRESENT.value
    image_credentials_name: Optional[str] = None
    dockerfile: Optional[str] = None
    build_target: Optional[str] = None
    args: Optional[Dict[str, str]] = None


class HookCmd(BaseModel):
    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)

    def __init__(self, **data):
        # FIXME 处理 proc_command 与 command/args 的关系
        if proc_command := data.get("proc_command"):
            data["command"] = None
            data["args"] = shlex.split(proc_command)
        super().__init__(**data)


class Hooks(BaseModel):
    pre_release: Optional[HookCmd] = None

    def __init__(self, **data):
        # db 旧数据使用了 camel case
        if pre_release := data.get("preRelease"):
            data["pre_release"] = pre_release

        super().__init__(**data)


class AddonSpec(BaseModel):
    name: str
    value: str


class Addon(BaseModel):
    """Addon for app module

    :param name: The name of the addon.
    :param specs: The specs of the addon.
    :param shared_from_module: The module name the addon is shared from.
    """

    name: str
    specs: Optional[List[AddonSpec]] = Field(default_factory=list)
    shared_from_module: Optional[str] = None


class ExecAction(BaseModel):
    command: List[str]


class HTTPHeader(BaseModel):
    name: str
    value: str


class HTTPGetAction(BaseModel):
    port: Union[int, str]
    host: Optional[str] = None
    path: Optional[str] = None
    http_headers: List[HTTPHeader] = Field(default_factory=list)
    scheme: Optional[Literal["HTTP", "HTTPS"]] = None


class TCPSocketAction(BaseModel):
    port: Union[int, str]
    host: Optional[str] = None


@register
class ProbeHandler(BaseModel):
    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None


class Probe(BaseModel):
    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None

    initial_delay_seconds: Optional[int] = 0
    timeout_seconds: Optional[int] = 1
    period_seconds: Optional[int] = 10
    success_threshold: Optional[int] = 1
    failure_threshold: Optional[int] = 3

    def get_probe_handler(self) -> ProbeHandler:
        return ProbeHandler(exec=self.exec, http_get=self.http_get, tcp_socket=self.tcp_socket)


@register
class ProbeSet(BaseModel):
    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None


class Process(BaseModel):
    name: str

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    # proc_command 表示单行 shell 命令, 与 command/args 二选一, 用于设置 Procfile 文件中进程的 command
    proc_command: Optional[str] = None

    target_port: Optional[int] = None

    # `None` value means the replicas is not specified.
    replicas: Optional[int] = None
    res_quota_plan: Optional[ResQuotaPlan] = None
    autoscaling: Optional[AutoscalingConfig] = None

    probes: Optional[ProbeSet] = None

    def __init__(self, **data):
        data["name"] = data["name"].lower()

        # FIXME 处理 proc_command 与 command/args 的关系
        if proc_command := data.get("proc_command"):
            data["command"] = None
            data["args"] = shlex.split(proc_command)

        super().__init__(**data)

    def get_proc_command(self) -> str:
        """get_proc_command: 生成 Procfile 文件中对应的命令行"""
        if self.proc_command:
            return self.proc_command
        return generate_bash_command_with_tokens(self.command or [], self.args or [])
