# -*- coding: utf-8 -*-
from typing import Dict, List

import cattr

from paas_wl.platform.applications.models.app import App
from paas_wl.workloads.resource_templates.components.probe import Probe, default_readiness_probe
from paas_wl.workloads.resource_templates.components.volume import Volume, VolumeMount
from paas_wl.workloads.resource_templates.constants import AppAddOnType
from paas_wl.workloads.resource_templates.models import AppAddOn


class AddonManager:
    def __init__(self, app: App):
        self.app = app

    def get_readiness_probe(self) -> Probe:
        try:
            return cattr.structure(
                AppAddOn.objects.get(app=self.app, template__type=AppAddOnType.READINESS_PROBE).render_spec(), Probe
            )
        except AppAddOn.DoesNotExist:
            return default_readiness_probe

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
