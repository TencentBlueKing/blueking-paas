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
import cattr

from paas_wl.workloads.processes.models import ProcessProbe
from paasng.extensions.declarative.deployment.resources import Probe
from paasng.platform.applications.models import ModuleEnvironment


def create_process_probe(
    env: ModuleEnvironment,
    process_type: str,
    probe_type: str,
    probe: Probe,
):
    """更新或创建应用探针的配置"""
    instance, _ = ProcessProbe.objects.update_or_create(
        defaults={
            "probe_handler": cattr.unstructure(probe.get_probe_handler()),
            "initial_delay_seconds": probe.initial_delay_seconds,
            "timeout_seconds": probe.timeout_seconds,
            "period_seconds": probe.period_seconds,
            "success_threshold": probe.success_threshold,
            "failure_threshold": probe.failure_threshold,
        },
        app=env.wl_app,
        process_type=process_type,
        probe_type=probe_type,
    )


def delete_process_probe(
    env: ModuleEnvironment,
    process_type: str,
):
    """删除应用探针的配置"""
    ProcessProbe.objects.filter(app=env.wl_app, process_type=process_type).delete()
