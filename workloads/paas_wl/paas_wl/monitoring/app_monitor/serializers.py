# -*- coding: utf-8 -*-
from rest_framework import serializers

from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor


class AppMetricsMonitorLSZ(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if "target_port" not in data:
            data["target_port"] = data.get("port")
        return super().to_internal_value(data)

    class Meta:
        model = AppMetricsMonitor
        exclude = ('app', 'created', 'updated')
