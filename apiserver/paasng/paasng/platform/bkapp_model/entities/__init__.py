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

from .addons import Addon, AddonSpec
from .build import AppBuildConfig
from .domain_resolution import DomainResolution, HostAlias
from .env_vars import EnvVar, EnvVarOverlay
from .hooks import HookCmd, Hooks
from .mounts import ConfigMapSource, Mount, MountOverlay, PersistentStorage, VolumeSource
from .probes import ExecAction, HTTPGetAction, HTTPHeader, Probe, ProbeHandler, ProbeSet, TCPSocketAction
from .proc_env_overlays import AutoscalingOverlay, ProcEnvOverlay, ReplicasOverlay, ResQuotaOverlay
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
    "EnvVarOverlay",
    "AutoscalingOverlay",
    "ReplicasOverlay",
    "ResQuotaOverlay",
    "ProcEnvOverlay",
    "MountOverlay",
    "ProcService",
]
