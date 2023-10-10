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
from typing import Dict, List, Optional

import cattr
from attrs import define, field, validators

from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.applications.constants import AppLanguage
from paasng.utils.validators import RE_CONFIG_VAR_KEY


@define
class EnvVariable:
    key: str = field(validator=validators.matches_re(RE_CONFIG_VAR_KEY))
    value: str
    description: Optional[str] = field(default=None, validator=validators.optional(validators.max_len(200)))
    environment_name: Optional[ConfigVarEnvName] = None

    def is_within_scope(self, given_env: ConfigVarEnvName) -> bool:
        """判断当前的环境变量在所给的环境中是否生效"""
        if self.environment_name is None or self.environment_name == ConfigVarEnvName.GLOBAL:
            return True
        return self.environment_name == given_env


@define
class BkSaaSItem:
    """Resource: An item representing an application and an optional module."""

    bk_app_code: str
    module_name: Optional[str] = None


@define
class SvcDiscovery:
    """Resource: Service discovery config

    :param bk_saas: List of `SaaSSvcItem`
    """

    bk_saas: List[BkSaaSItem] = field(factory=list)


@define
class ExecAction:
    command: List[str]


@define
class HTTPHeader:
    name: str
    value: str


@define
class HTTPGetAction:
    port: str
    host: Optional[str] = None
    path: Optional[str] = None
    http_headers: Optional[List[HTTPHeader]] = None
    scheme: Optional[str] = None


@define
class TCPSocketAction:
    port: str
    host: Optional[str] = None


@define
class ProbeHandler:
    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None


@define
class Probe:
    """Resource: Probe

    :param exec:命令行探活检测机制
    :param http_get:http 请求探活检测机制
    :param tcp_socket:tcp 请求探活检测机制
    :param initial_delay_seconds:容器启动后等待时间
    :param timeout_seconds:探针执行超时时间
    :param period_seconds:探针执行间隔时间
    :param success_threshold:连续几次检测成功后，判定容器是健康的
    :param failure_threshold:连续几次检测失败后，判定容器是不健康
    """

    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None

    initial_delay_seconds: Optional[int] = 0
    timeout_seconds: Optional[int] = 1
    period_seconds: Optional[int] = 10
    success_threshold: Optional[int] = 1
    failure_threshold: Optional[int] = 3

    def get_probe_handler(self) -> ProbeHandler:
        """返回 ProbeHandler 对象 """
        return ProbeHandler(exec=self.exec, http_get=self.http_get, tcp_socket=self.tcp_socket)


@define
class ProbeSet:
    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None


@define
class Process:
    """Resource: Process

    :param command: 启动指令
    :param replicas: 副本数
    :param plan: 资源方案名称
    """

    command: str
    replicas: Optional[int] = field(default=None, validator=validators.optional(validators.gt(0)))
    plan: Optional[str] = None
    probes: Optional[ProbeSet] = None


@define
class Scripts:
    """Resource: Scripts

    :param pre_release_hook: 部署前置指令
    """

    pre_release_hook: str = ""


@define
class BluekingMonitor:
    """Resource: BluekingMonitor

    :param port: Service 暴露的端口号
    :param target_port: Service 关联的容器内的端口号, 不设置则使用 port
    """

    port: int
    target_port: Optional[int] = None

    def __attrs_post_init__(self):
        if self.target_port is None:
            self.target_port = self.port


@define
class DeploymentDesc:
    """Resource: Deployment description

    :param language: 应用开发语言
    :param source_dir: 源码目录
    :param env_variables: 部署时使用的环境变量
    :param processes: 启动进程
    :param scripts: 部署钩子
    :param svc_discovery: 服务发现
    :param monitor: SaaS 监控采集配置
    """

    language: AppLanguage
    source_dir: str = ""
    env_variables: List[EnvVariable] = field(factory=list)
    processes: Dict[str, Process] = field(factory=dict)
    scripts: Scripts = field(factory=Scripts)
    svc_discovery: SvcDiscovery = field(factory=SvcDiscovery)
    bk_monitor: Optional[BluekingMonitor] = None

    def get_procfile(self) -> Dict[str, str]:
        return {key: process.command for key, process in self.processes.items()}

    def get_env_variables(self, environment_name: Optional[ConfigVarEnvName] = None):
        if environment_name is None or environment_name == ConfigVarEnvName.GLOBAL:
            return cattr.unstructure(self.env_variables)
        return cattr.unstructure(
            [env_var for env_var in self.env_variables if env_var.is_within_scope(environment_name)]
        )
