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

from paasng.utils.structure import register

from .entities import (
    Addon,
    AppBuildConfig,
    AutoscalingOverlay,
    DomainResolution,
    EnvVar,
    EnvVarOverlay,
    Hooks,
    Mount,
    MountOverlay,
    Process,
    ReplicasOverlay,
    ResQuotaOverlay,
    SvcDiscConfig,
)


class BkAppConfiguration(BaseModel):
    """Configuration for BkApp"""

    env: List[EnvVar] = Field(default_factory=list)


class BkAppEnvOverlay(BaseModel):
    """Defines environment specified configs"""

    replicas: Optional[List[ReplicasOverlay]] = None
    res_quotas: Optional[List[ResQuotaOverlay]] = None
    env_variables: Optional[List[EnvVarOverlay]] = None
    autoscaling: Optional[List[AutoscalingOverlay]] = None
    mounts: Optional[List[MountOverlay]] = None


@register
class BkAppSpec(BaseModel):
    build: Optional[AppBuildConfig] = None
    processes: List[Process] = Field(default_factory=list)
    hooks: Optional[Hooks] = None
    addons: List[Addon] = Field(default_factory=list)
    mounts: Optional[List[Mount]] = None
    configuration: BkAppConfiguration = Field(default_factory=BkAppConfiguration)
    domain_resolution: Optional[DomainResolution] = None
    svc_discovery: Optional[SvcDiscConfig] = None
    env_overlay: Optional[BkAppEnvOverlay] = None
