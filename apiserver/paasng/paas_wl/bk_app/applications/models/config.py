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

import logging
from typing import List, Optional

from attrs import define, field
from django.conf import settings
from django.db import models
from jsonfield import JSONField

from paas_wl.bk_app.applications.models import UuidAuditedModel
from paas_wl.utils.models import make_json_field
from paas_wl.workloads.release_controller.constants import ImagePullPolicy, RuntimeType

logger = logging.getLogger(__name__)


@define
class RuntimeConfig:
    """App Runtime Configs, includes the image, type, ENTRYPOINT and so on."""

    # [Deprecated] use Build.image instead
    image: Optional[str] = None
    type: RuntimeType = field(default=RuntimeType.BUILDPACK)
    # [Deprecated] use entrypoint instead
    endpoint: List[str] = field(factory=list)
    entrypoint: List[str] = field(factory=list)
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)

    def get_image_pull_policy(self) -> ImagePullPolicy:
        try:
            return ImagePullPolicy(self.image_pull_policy)
        except ValueError:
            return ImagePullPolicy.IF_NOT_PRESENT


RuntimeConfigField = make_json_field("RuntimeConfigField", py_model=RuntimeConfig)


class Config(UuidAuditedModel):
    """App configs, includes env variables and resource limits

    [multi-tenancy] TODO
    """

    owner = models.CharField(max_length=64)
    app = models.ForeignKey("App", on_delete=models.CASCADE)
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
        get_latest_by = "created"
        ordering = ["-created"]
        unique_together = (("app", "uuid"),)

    def get_image(self) -> str:
        """Return settings.DEFAULT_SLUGRUNNER_IMAGE when self.image is not set

        # deprecated: use Build.get_image instead
        """
        if self.runtime.image:
            return self.runtime.image
        return self.image or settings.DEFAULT_SLUGRUNNER_IMAGE

    @property
    def envs(self):
        # TODO add other env values such as service resource
        return self.values
