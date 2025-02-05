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

import hashlib
import json
from typing import Dict, List, Union

from django.db import models

from paas_wl.bk_app.applications.models import UuidAuditedModel, WlApp
from paas_wl.infras.resource_templates.constants import AppAddOnType
from paasng.core.tenant.fields import tenant_id_field_factory


class AppAddOnTemplate(UuidAuditedModel):
    """应用挂件模版

    [multi-tenancy] This model is not tenant-aware.
    """

    region = models.CharField(max_length=32)
    name = models.CharField("模版名", max_length=64)
    spec = models.TextField("资源内容")
    enabled = models.BooleanField("资源启用", default=True)
    type = models.IntegerField("挂件类型", default=AppAddOnType.SIMPLE_SIDECAR.value)

    class Meta:
        unique_together = ("region", "name")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.spec).hexdigest()

    def link_to_app(self, app: WlApp) -> "AppAddOn":
        add_on, _ = AppAddOn.objects.get_or_create(app=app, template=self, defaults={"tenant_id": app.tenant_id})
        add_on.sync_with_template()
        return add_on


class AppAddOnManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enabled=True, template__enabled=True)


class AppAddOn(UuidAuditedModel):
    """应用挂件关联实例"""

    app = models.ForeignKey(WlApp, related_name="add_ons", on_delete=models.CASCADE)
    template = models.ForeignKey(AppAddOnTemplate, related_name="instances", on_delete=models.CASCADE)
    enabled = models.BooleanField("是否启用", default=True)
    spec = models.TextField("资源内容")
    tenant_id = tenant_id_field_factory()

    objects = AppAddOnManager()
    default_objects = models.Manager()

    def render_spec(self) -> Union[List, Dict]:
        """Return deserialized `spec`"""
        return json.loads(self.spec.strip())

    def sync_with_template(self):
        """与模版内容同步"""
        self.spec = self.template.spec
        self.save(update_fields=["spec", "updated"])

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.spec).hexdigest()
