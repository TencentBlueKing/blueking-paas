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

from .addons import sync_addons
from .build import sync_build
from .domain_resolution import sync_domain_resolution
from .env_overlays import sync_env_overlays, sync_proc_env_overlay
from .env_vars import sync_env_vars, sync_preset_env_vars
from .hooks import sync_hooks
from .mounts import sync_mounts
from .processes import sync_processes
from .svc_discovery import sync_svc_discovery

__all__ = [
    "sync_addons",
    "sync_build",
    "sync_domain_resolution",
    "sync_env_overlays",
    "sync_proc_env_overlay",
    "sync_env_vars",
    "sync_preset_env_vars",
    "sync_hooks",
    "sync_mounts",
    "sync_processes",
    "sync_svc_discovery",
]
