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

from typing import List, Optional

from pydantic import BaseModel, Field

from paasng.utils.structure import NOTSET, AllowNotsetModel, NotSetType, prepare_json_field

from .addons import Addon
from .build import AppBuildConfig
from .components import Component
from .domain_resolution import DomainResolution
from .env_vars import EnvVar, EnvVarOverlay
from .hooks import Hooks
from .mounts import Mount, MountOverlay
from .observability import Observability
from .proc_env_overlays import AutoscalingOverlay, ReplicasOverlay, ResQuotaOverlay
from .processes import Process
from .svc_discovery import SvcDiscConfig


class BkAppConfiguration(BaseModel):
    """Configuration for BkApp"""

    env: List[EnvVar] = Field(default_factory=list)


class BkAppEnvOverlay(AllowNotsetModel):
    """Defines environment specified configs"""

    # TODO: Should we stop support `None` as a possible value?
    replicas: List[ReplicasOverlay] | NotSetType | None = NOTSET
    res_quotas: List[ResQuotaOverlay] | NotSetType | None = NOTSET
    env_variables: List[EnvVarOverlay] | NotSetType | None = NOTSET
    autoscaling: List[AutoscalingOverlay] | NotSetType | None = NOTSET
    mounts: Optional[List[MountOverlay]] | NotSetType | None = NOTSET


@prepare_json_field
class BkAppSpec(AllowNotsetModel):
    """BkAppSpec(snake-case format)

    :param build: 构建配置
    :param processes: 进程配置
    :param hooks: 钩子配置
    :param addons: 增强服务配置
    :param mounts: 挂载配置
    :param configuration: 环境变量配置
    :param domain_resolution: 域名解析
    :param svc_discovery: 服务发现
    :param env_overlay: 分环境重写配置
    :param observability: 可观测功能配置
    :param components: 进程组件
    """

    build: Optional[AppBuildConfig] = None
    processes: List[Process] = Field(default_factory=list)
    hooks: Hooks | NotSetType | None = NOTSET
    addons: List[Addon] = Field(default_factory=list)
    mounts: Optional[List[Mount]] = None
    configuration: BkAppConfiguration = Field(default_factory=BkAppConfiguration)
    domain_resolution: DomainResolution | NotSetType | None = NOTSET
    svc_discovery: SvcDiscConfig | NotSetType | None = NOTSET
    env_overlay: BkAppEnvOverlay | NotSetType | None = NOTSET
    observability: Optional[Observability] = None
    components: Optional[List[Component]] = None
