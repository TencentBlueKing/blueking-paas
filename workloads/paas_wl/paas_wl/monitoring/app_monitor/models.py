# -*- coding: utf-8 -*-
from django.db import models

from paas_wl.platform.applications.models import App, AuditedModel


class AppMetricsMonitor(AuditedModel):
    app = models.OneToOneField(App, on_delete=models.CASCADE, db_constraint=False)
    is_enabled = models.BooleanField(help_text="是否启动 AppMetrics", default=True)
    port = models.IntegerField(help_text="Service 端口")
    target_port = models.IntegerField(help_text="容器内的端口")

    def disable(self):
        self.is_enabled = False
        self.save(update_fields=["is_enabled", "updated"])
