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
"""entities 中存放着与应用模型相关的实体数据类，比如：进程、探针配置和环境变量等。大部分实体类
的字段结构与 BkApp 应用模型定义中的对应类型对应（只是命名规则驼峰变为蛇形）。不过，请不要将它们
简单和“应用模型规范”中的内容划等号，因为它们原则上和模型规范的“版本”（v1alpha1/v1beta1/...）无关。

当前主要在“导入BkApp 资源 YAML”时，作为中转数据类使用。

这些实体数据类的特点：

- 使用蛇形命名法（foo_var），和项目其他内部数据类保持一致
- 结构扁平，仅包含纯粹数据字段，比如环境变量仅有 name 和 value，没有“所属应用”信息
- 不包含数据定义之外的复杂逻辑，仅承担数据类的简单职责
"""

from .addons import Addon, AddonSpec
from .build import AppBuildConfig
from .components import Component
from .domain_resolution import DomainResolution, HostAlias
from .env_vars import EnvVar, EnvVarOverlay
from .hooks import HookCmd, Hooks
from .mounts import ConfigMapSource, Mount, MountOverlay, PersistentStorage, VolumeSource
from .observability import Metric, Monitoring, Observability
from .probes import ExecAction, HTTPGetAction, HTTPHeader, Probe, ProbeHandler, ProbeSet, TCPSocketAction
from .proc_env_overlays import AutoscalingOverlay, ReplicasOverlay, ResQuotaOverlay
from .proc_service import ProcService
from .processes import Process
from .scaling_config import AutoscalingConfig
from .svc_discovery import SvcDiscConfig, SvcDiscEntryBkSaaS

__all__ = [
    "Process",
    "AutoscalingConfig",
    "ProbeSet",
    "ProbeHandler",
    "Probe",
    "ExecAction",
    "HTTPGetAction",
    "HTTPHeader",
    "TCPSocketAction",
    "HookCmd",
    "Hooks",
    "AppBuildConfig",
    "AddonSpec",
    "Addon",
    "DomainResolution",
    "HostAlias",
    "SvcDiscConfig",
    "SvcDiscEntryBkSaaS",
    "ConfigMapSource",
    "PersistentStorage",
    "VolumeSource",
    "Mount",
    "EnvVar",
    # env-overlay types
    "EnvVarOverlay",
    "AutoscalingOverlay",
    "ReplicasOverlay",
    "ResQuotaOverlay",
    "MountOverlay",
    # proc-service types
    "ProcService",
    # observability types
    "Monitoring",
    "Observability",
    "Metric",
    # component types
    "Component",
]
