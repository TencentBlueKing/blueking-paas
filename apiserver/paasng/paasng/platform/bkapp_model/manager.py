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

from dataclasses import asdict
from typing import Dict, Optional, Union

from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module


class ModuleProcessSpecManager:
    """The manager for ModuleProcessSpec objects."""

    def __init__(self, module: Module):
        self.module = module

    def set_replicas(self, proc_name: str, env_name: str, replicas: int):
        """Set the replicas for the given process and environment."""
        proc_spec = ModuleProcessSpec.objects.get(module=self.module, name=proc_name)
        if proc_spec.get_target_replicas(env_name) != replicas:
            ProcessSpecEnvOverlay.objects.update_or_create(
                proc_spec=proc_spec,
                environment_name=AppEnvName(env_name).value,
                defaults={"target_replicas": replicas, "tenant_id": proc_spec.tenant_id},
            )

    def set_autoscaling(
        self, proc_name: str, env_name: str, enabled: bool, config: Optional[AutoscalingConfig] = None
    ):
        """Set the autoscaling for the given process and environment."""
        proc_spec = ModuleProcessSpec.objects.get(module=self.module, name=proc_name)
        defaults: Dict[str, Union[bool, Dict, None]] = {"tenant_id": proc_spec.tenant_id, "autoscaling": enabled}
        if config is not None:
            defaults.update(scaling_config=asdict(config))

        ProcessSpecEnvOverlay.objects.update_or_create(
            proc_spec=proc_spec,
            environment_name=AppEnvName(env_name).value,
            defaults=defaults,
        )
