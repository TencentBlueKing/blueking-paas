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

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.conf import settings

from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.workloads.release_controller.constants import ImagePullPolicy


class HealthPhase(StrStructuredEnum):
    HEALTHY = EnumField("Healthy")
    PROGRESSING = EnumField("Progressing")
    UNHEALTHY = EnumField("Unhealthy")
    UNKNOWN = EnumField("Unknown")


@dataclass
class Runtime:
    """容器运行相关配置"""

    envs: Dict[str, str]
    image: str
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.ALWAYS)


@dataclass
class ResourceSpec:
    cpu: str
    memory: str

    def to_dict(self):
        return {
            "cpu": self.cpu,
            "memory": self.memory,
        }


@dataclass
class Resources:
    """计算资源定义"""

    limits: Optional[ResourceSpec] = None
    requests: Optional[ResourceSpec] = None

    def to_dict(self):
        d = {}
        if self.limits:
            d["limits"] = self.limits.to_dict()
        if self.requests:
            d["requests"] = self.requests.to_dict()
        return d


@dataclass
class Status:
    replicas: int
    ready_replicas: int

    def to_health_phase(self) -> str:
        if self.replicas == self.ready_replicas:
            return HealthPhase.HEALTHY

        # TODO 如果需要细化出 Unhealthy, 可以结合 Conditions 处理
        # 将 Unhealthy 也并入 Progressing, 简化需求
        return HealthPhase.PROGRESSING


@dataclass
class ServicePortPair:
    """Service port pair"""

    name: str
    port: int
    target_port: int
    protocol: str = "TCP"


@dataclass
class IngressPathBackend:
    """Ingress Path Backend object"""

    path_prefix: str
    service_name: str
    service_port_name: str


@dataclass
class IngressDomain:
    """Ingress Domain object"""

    host: str
    path_backends: List[IngressPathBackend]
    tls_enabled: bool = False
    tls_secret_name: str = ""


@dataclass
class DevSandboxDetail:
    url: str
    envs: Dict[str, str]
    status: str


class DevSandboxWithCodeEditorUrls:
    app_url: str
    devserver_url: str
    code_editor_url: str
    code_editor_health_url: str

    def __init__(self, base_url: str, dev_sandbox_code: str):
        self.app_url = f"{base_url}/dev_sandbox/{dev_sandbox_code}/app/"
        self.devserver_url = f"{base_url}/dev_sandbox/{dev_sandbox_code}/devserver/"
        self.code_editor_url = (
            f"{base_url}/dev_sandbox/{dev_sandbox_code}/code-editor/?folder={settings.CODE_EDITOR_START_DIR}"
        )
        self.code_editor_health_url = f"{base_url}/dev_sandbox/{dev_sandbox_code}/code-editor/healthz"


@dataclass
class DevSandboxWithCodeEditorDetail:
    dev_sandbox_env_vars: Dict[str, str]
    code_editor_env_vars: Dict[str, str]
    dev_sandbox_status: str
    code_editor_status: str
    urls: DevSandboxWithCodeEditorUrls


@dataclass
class SourceCodeConfig:
    """源码持久化相关配置"""

    # 源码持久化用的 pvc 名称
    pvc_claim_name: Optional[str] = None
    # 工作空间，用于读取/存储源码
    workspace: Optional[str] = None
    # 源码获取地址
    source_fetch_url: Optional[str] = None
    # 源码获取方式
    source_fetch_method: SourceCodeFetchMethod = SourceCodeFetchMethod.HTTP


@dataclass
class CodeEditorConfig:
    """代码编辑器相关配置"""

    # 源码持久化用的 pvc 名称
    pvc_claim_name: Optional[str] = None
    # 项目目录, 读取项目源码的起始目录
    start_dir: Optional[str] = None
    # 登陆密码
    password: Optional[str] = None
