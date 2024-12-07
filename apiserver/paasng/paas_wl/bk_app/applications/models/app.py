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

from django.db import models
from django.utils.functional import cached_property
from jsonfield import JSONField

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import UuidAuditedModel
from paas_wl.bk_app.applications.models.validators import validate_app_name, validate_app_structure

logger = logging.getLogger(__name__)


# Deprecated: 名称 App 容易与其他概念混淆，请使用别名 WlApp
class App(UuidAuditedModel):
    """App Model"""

    owner = models.CharField(max_length=64)
    region = models.CharField(max_length=32)
    name = models.SlugField(max_length=64, validators=[validate_app_name], unique=True)
    # deprecated field
    structure = JSONField(default={}, blank=True, validators=[validate_app_structure])
    type = models.CharField(verbose_name="应用类型", max_length=16, default=WlAppType.DEFAULT.value, db_index=True)

    @cached_property
    def scheduler_safe_name(self):
        """app name in scheduler backend"""
        return self.name.replace("_", "0us0")

    @property
    def scheduler_safe_name_with_region(self):
        return f"{self.region}-{self.scheduler_safe_name}"

    @cached_property
    def namespace(self):
        # Both default and cloud-native are using this method to get namespace at this moment.
        # The namespace of the cloud-native app follow naming rules that do not include the module name.

        if self.type == WlAppType.CLOUD_NATIVE.value:
            from paasng.platform.engine.models import EngineApp
            from paasng.platform.modules.constants import DEFAULT_ENGINE_APP_PREFIX

            module_env = EngineApp.objects.get(region=self.region, name=self.name).env
            cnative_ns = f"{DEFAULT_ENGINE_APP_PREFIX}-{module_env.application.code}-{module_env.environment}"
            return cnative_ns.replace("_", "0us0")

        return self.scheduler_safe_name

    @cached_property
    def module_name(self):
        from paas_wl.bk_app.applications.managers import get_metadata

        return get_metadata(self).module_name

    @property
    def latest_config(self):
        return self.config_set.latest()

    @property
    def use_dev_sandbox(self) -> bool:
        return self.name.endswith("-dev")

    def __str__(self) -> str:
        return f"<{self.name}, region: {self.region}, type: {self.type}>"


# Alias names to distinguish from Platform's App(Application/BluekingApplication) model
WlApp = App
