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
import logging
import shlex
from typing import Dict, List, Optional

from attrs import define, field
from django.conf import settings
from django.db import models
from jsonfield import JSONField

from paas_wl.platform.applications.models import UuidAuditedModel
from paas_wl.release_controller.constants import ImagePullPolicy, RuntimeType
from paas_wl.utils.models import make_json_field

logger = logging.getLogger(__name__)


@define
class RuntimeConfig:
    """App Runtime Configs, includes the image, type, ENTRYPOINT and so on."""

    image: Optional[str] = None
    type: RuntimeType = field(default=RuntimeType.BUILDPACK)
    endpoint: List[str] = field(factory=list)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)

    def get_entrypoint(self) -> List[str]:
        if self.type == RuntimeType.CUSTOM_IMAGE:
            return ["env"]
        return self.endpoint or ['bash', '/runner/init']

    def get_image_pull_policy(self) -> ImagePullPolicy:
        try:
            return ImagePullPolicy(self.image_pull_policy)
        except ValueError:
            return ImagePullPolicy.IF_NOT_PRESENT

    def get_command(self, command_type: str, procfile: Dict[str, str]) -> List[str]:
        if self.type == RuntimeType.BUILDPACK:
            return ["start", command_type]
        return shlex.split(procfile[command_type])


RuntimeConfigField = make_json_field("RuntimeConfigField", py_model=RuntimeConfig)


class Config(UuidAuditedModel):
    """App configs, includes env variables and resource limits"""

    owner = models.CharField(max_length=64)
    app = models.ForeignKey('App', on_delete=models.CASCADE)
    values = JSONField(default={}, blank=True)
    resource_requirements = JSONField(default={}, blank=True)
    node_selector = JSONField(default={}, blank=True)
    domain = models.CharField("domain", max_length=64, default="")
    tolerations = JSONField(default=[], blank=True)
    cluster = models.CharField(max_length=64, default="", blank=True)
    image = models.CharField(max_length=256, null=True)
    # Essential config data, include variables such as "PaaS AppCode" etc.
    metadata = JSONField(null=True, blank=True)
    runtime: RuntimeConfig = RuntimeConfigField(default=RuntimeConfig)
    mount_log_to_host = models.BooleanField(default=True, help_text="Whether mount app logs to host")

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        unique_together = (('app', 'uuid'),)

    def get_image(self) -> str:
        """Return settings.DEFAULT_SLUGRUNNER_IMAGE when self.image is not set"""
        if self.runtime.image:
            return self.runtime.image
        return self.image or settings.DEFAULT_SLUGRUNNER_IMAGE

    def refresh_res_reqs(self):
        """Refresh resource_requirements field"""
        from paas_wl.workloads.processes.models import ProcessSpec

        self.resource_requirements = {
            pack.name: pack.plan.get_resource_summary()
            for pack in ProcessSpec.objects.filter(engine_app_id=self.app.pk)
        }
        self.save(update_fields=['resource_requirements'])

    @property
    def envs(self):
        # TODO add other env values such as service resource
        return self.values
