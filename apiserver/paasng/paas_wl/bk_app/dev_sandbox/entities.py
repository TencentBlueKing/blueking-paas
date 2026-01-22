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

from collections import UserList
from typing import Collection, Dict, List

from attrs import asdict, define, field

from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvVarSource, SourceCodeFetchMethod
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.utils.masked_curlify import MASKED_CONTENT

from .constants import DEV_SANDBOX_SENSITIVE_ENV_VARS


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


@define
class DevSandboxEnvVar:
    """
    开发沙箱环境变量
    is_sensitive 需要由创建方显式传入，可用 is_sensitive() 帮助方法统一判断逻辑
    """

    key: str
    value: str
    source: DevSandboxEnvVarSource
    is_sensitive: bool = False

    def to_dict(self) -> Dict[str, str]:
        data = asdict(self)
        return data

    def to_masked_dict(self) -> Dict[str, str]:
        """
        返回屏蔽敏感信息的字典表示， 可用于 API 输出或日志
        """
        data = self.to_dict()
        if self.is_sensitive:
            data["value"] = MASKED_CONTENT
        return data

    def __repr__(self):
        return (
            f"DevSandboxEnvVar(key={self.key}, value={MASKED_CONTENT if self.is_sensitive else self.value},"
            + f" source={self.source}, sensitive={self.is_sensitive})"
        )


def is_sensitive(key: str, to_check: Collection[str] | None = None) -> bool:
    """
    检查key是否为敏感字段: key 是否存在于 DEV_SANDBOX_SENSITIVE_ENV_VARS 和 to_check 中

    :param key: 需要检查的字段名
    :param to_check: 额外指定的敏感字段集合
    """
    if to_check and key in to_check:
        return True
    return key in DEV_SANDBOX_SENSITIVE_ENV_VARS


class DevSandboxEnvVarList(UserList):
    """A list of DevSandboxEnvVar."""

    @property
    def map(self) -> Dict[str, DevSandboxEnvVar]:
        return {item.key: item for item in self}

    @property
    def kv_map(self):
        return {item.key: item.value for item in self}

    @property
    def masked_list(self):
        return [item.to_masked_dict() for item in self]

    @property
    def list(self):
        return [item.to_dict() for item in self]

    @classmethod
    def from_kv_map(
        cls,
        kv_map: Dict[str, str],
        source: DevSandboxEnvVarSource,
        sensitive_fields: Collection[str] | None = None,
    ) -> "DevSandboxEnvVarList":
        return cls(
            [
                DevSandboxEnvVar(
                    key=key,
                    value=value,
                    source=source,
                    is_sensitive=is_sensitive(key, sensitive_fields),
                )
                for key, value in kv_map.items()
            ]
        )
