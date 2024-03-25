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
import json
from typing import Dict, List, Optional

import cattr
from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.constants import ProbeType
from paas_wl.bk_app.processes.models import ProcessProbe
from paas_wl.infras.resource_templates.components.probe import Probe, get_default_readiness_probe
from paas_wl.infras.resource_templates.components.volume import Volume, VolumeMount
from paas_wl.infras.resource_templates.constants import AppAddOnType
from paas_wl.infras.resource_templates.models import AppAddOn
from paas_wl.utils.basic import convert_key_to_camel


class ProcessProbeManager:
    def __init__(self, app: WlApp, process_type: str):
        self.app = app
        self.process_type = process_type

    def get_probe(self, probe_type: str) -> Optional[Probe]:
        try:
            process_probe: ProcessProbe = ProcessProbe.objects.get(
                app=self.app, process_type=self.process_type, probe_type=probe_type
            )
        except ProcessProbe.DoesNotExist:
            return None

        probe_handler = convert_key_to_camel(cattr.unstructure(process_probe.probe_handler))
        # 占位符 ${PORT} 替换为环境变量 PORT
        probe_handler = _render_by_env(probe_handler)
        parameters_json = {
            "initialDelaySeconds": process_probe.initial_delay_seconds,
            "timeoutSeconds": process_probe.timeout_seconds,
            "periodSeconds": process_probe.period_seconds,
            "successThreshold": process_probe.success_threshold,
            "failureThreshold": process_probe.failure_threshold,
        }
        combined_json = {**probe_handler, **parameters_json}

        return cattr.structure(combined_json, Probe)

    def get_readiness_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type=ProbeType.READINESS)

    def get_liveness_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type=ProbeType.LIVENESS)

    def get_startup_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type=ProbeType.STARTUP)


def _render_by_env(data: dict) -> dict:
    template_str = json.dumps(data)

    # 检查template_str是否包含$PORT
    if "${PORT}" in template_str:
        if not settings.CONTAINER_PORT:
            raise ValueError("The 'port' environment variable for ProcessProbe is empty")
        rendered_str = template_str.replace("${PORT}", str(settings.CONTAINER_PORT))
    else:
        rendered_str = template_str

    return json.loads(rendered_str)


class AddonManager:
    def __init__(self, app: WlApp):
        self.app = app

    def get_readiness_probe(self) -> Probe:
        try:
            return cattr.structure(
                AppAddOn.objects.get(app=self.app, template__type=AppAddOnType.READINESS_PROBE).render_spec(), Probe
            )
        except AppAddOn.DoesNotExist:
            return get_default_readiness_probe()

    def get_sidecars(self) -> List[Dict]:
        return [
            add_on.render_spec()
            for add_on in AppAddOn.objects.filter(app=self.app, template__type=AppAddOnType.SIMPLE_SIDECAR)
        ]

    def get_volumes(self) -> List[Volume]:
        volumes = [
            cattr.structure(add_on.render_spec(), Volume)
            for add_on in AppAddOn.objects.filter(app=self.app, template__type=AppAddOnType.VOLUME)
        ]
        return volumes

    def get_volume_mounts(self) -> List[VolumeMount]:
        mounts = [
            cattr.structure(add_on.render_spec(), VolumeMount)
            for add_on in AppAddOn.objects.filter(app=self.app, template__type=AppAddOnType.VOLUME_MOUNT)
        ]
        return mounts
