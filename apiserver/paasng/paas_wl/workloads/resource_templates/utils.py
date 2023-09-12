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
from typing import Dict, List, Optional

import cattr

from paas_wl.platform.applications.models import WlApp
from paas_wl.utils.basic import convert_dict_underscore_to_camel
from paas_wl.workloads.processes.models import WlAppProbe
from paas_wl.workloads.resource_templates.components.probe import Probe, get_default_readiness_probe
from paas_wl.workloads.resource_templates.components.volume import Volume, VolumeMount
from paas_wl.workloads.resource_templates.constants import AppAddOnType
from paas_wl.workloads.resource_templates.models import AppAddOn


class AppProbeManager:
    def __init__(self, app: WlApp, process_type: str):
        self.app = app
        self.process_type = process_type

    def get_probe(self, probe_type: str) -> Optional[Probe]:
        try:
            wlapp_probe: WlAppProbe = WlAppProbe.objects.get(
                app=self.app, process_type=self.process_type, probe_type=probe_type
            )
            check_mechanism_json = convert_dict_underscore_to_camel(wlapp_probe.check_mechanism)
            parameters_json = {
                'initialDelaySeconds': wlapp_probe.initial_delay_seconds,
                'timeoutSeconds': wlapp_probe.timeout_seconds,
                'periodSeconds': wlapp_probe.period_seconds,
                'successThreshold': wlapp_probe.success_threshold,
                'failureThreshold': wlapp_probe.failure_threshold,
            }
            combined_json = {**check_mechanism_json, **parameters_json}
            return cattr.structure(combined_json, Probe)
        except WlAppProbe.DoseNotExit:
            return None

    def get_readiness_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type='readiness')

    def get_liveness_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type='liveness')

    def get_startup_probe(self) -> Optional[Probe]:
        return self.get_probe(probe_type='startup')


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
