# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Dict, List, Union

from django.db import models

from paas_wl.platform.applications.models import UuidAuditedModel
from paas_wl.platform.applications.models.app import App
from paas_wl.workloads.resource_templates.constants import AppAddOnType


class AppAddOnTemplate(UuidAuditedModel):
    """应用挂件模版"""

    region = models.CharField(max_length=32)
    name = models.CharField("模版名", max_length=64)
    spec = models.TextField("资源内容")
    enabled = models.BooleanField("资源启用", default=True)
    type = models.IntegerField("挂件类型", default=AppAddOnType.SIMPLE_SIDECAR.value)

    class Meta:
        unique_together = ('region', 'name')

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.spec).hexdigest()

    def link_to_app(self, app: App) -> 'AppAddOn':
        add_on, _ = AppAddOn.objects.get_or_create(app=app, template=self)
        add_on.sync_with_template()
        return add_on


class AppAddOnManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enabled=True, template__enabled=True)


class AppAddOn(UuidAuditedModel):
    """应用挂件关联实例"""

    app = models.ForeignKey(App, related_name="add_ons", on_delete=models.CASCADE)
    template = models.ForeignKey(AppAddOnTemplate, related_name="instances", on_delete=models.CASCADE)
    enabled = models.BooleanField("是否启用", default=True)
    spec = models.TextField("资源内容")

    objects = AppAddOnManager()
    default_objects = models.Manager()

    def render_spec(self) -> Union[List, Dict]:
        """Return deserialized `spec`"""
        return json.loads(self.spec.strip())

    def sync_with_template(self):
        """与模版内容同步"""
        self.spec = self.template.spec
        self.save(update_fields=['spec', 'updated'])

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.spec).hexdigest()
