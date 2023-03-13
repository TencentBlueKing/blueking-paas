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
"""Main functionalities for proc module"""
from typing import List

from attrs import define

from paas_wl.cnative.specs.resource import get_mres_from_cluster
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource
from paas_wl.workloads.processes.constants import AppEnvName, ProcessTargetStatus
from paasng.platform.applications.models import ModuleEnvironment

from .replicas import ReplicasReader

# THe default maximum replicas for cloud-native apps's processes
DEFAULT_MAX_REPLICAS = 5


@define
class CNativeProcSpec:
    """Process spec for cloud-native apps, it has less properties than default
    app's ProcessSpec model, some fields includes "resource_limit" are removed.
    """

    name: str
    target_replicas: int
    target_status: str

    # TODO: Use dynamic limitation for each app
    max_replicas: int = DEFAULT_MAX_REPLICAS


def get_proc_specs(env: ModuleEnvironment) -> List[CNativeProcSpec]:
    """Get process specifications for env"""
    res = get_mres_from_cluster(env)
    if not res:
        return []
    return parse_proc_specs(res, AppEnvName(env.environment))


def parse_proc_specs(res: BkAppResource, env_name: AppEnvName) -> List[CNativeProcSpec]:
    """Parse process specifications from app model resource"""
    results = []
    counts = ReplicasReader(res).read_all(env_name)
    for name, (cnt, _) in counts.items():
        target_status = ProcessTargetStatus.START.value if cnt > 0 else ProcessTargetStatus.STOP.value
        results.append(CNativeProcSpec(name, cnt, target_status))
    return results
