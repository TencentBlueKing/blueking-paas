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

from attrs import asdict, define, field

from paas_wl.bk_app.dev_sandbox.constants import SourceCodeFetchMethod
from paas_wl.workloads.release_controller.constants import ImagePullPolicy


@define
class Runtime:
    """容器运行时"""

    envs: Dict[str, str]
    image: str
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.ALWAYS)


@define
class ResourceSpec:
    cpu: str
    memory: str


@define
class Resources:
    """运行资源"""

    limits: ResourceSpec | None = None
    requests: ResourceSpec | None = None

    def to_dict(self):
        quota = {}
        if self.limits:
            quota["limits"] = asdict(self.limits)
        if self.requests:
            quota["requests"] = asdict(self.requests)

        return quota


@define
class NetworkConfig:
    """网络相关配置（Ingress、Service 等使用）"""

    # Ingress 访问路径前缀
    path_prefix: str
    # Service 端口配置（名称，端口，容器端口）
    port_name: str
    port: int
    target_port: int


@define
class ServicePortPair:
    name: str
    port: int
    target_port: int
    protocol: str = "TCP"


@define
class IngressPathBackend:
    path_prefix: str
    service_name: str
    service_port_name: str


@define
class IngressDomain:
    """域名配置信息"""

    host: str
    path_backends: List[IngressPathBackend]
    tls_enabled: bool = False
    tls_secret_name: str = ""


@define
class SourceCodeConfig:
    """源码配置"""

    # 源码获取地址
    source_fetch_url: str | None = None
    # 源码获取方式
    source_fetch_method: SourceCodeFetchMethod = SourceCodeFetchMethod.HTTP


@define
class CodeEditorConfig:
    """代码编辑器配置"""

    # 登录密码
    password: str
