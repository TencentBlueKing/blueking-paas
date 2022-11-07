# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response

from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.monitoring.app_monitor.serializers import AppMetricsMonitorLSZ
from paas_wl.platform.system_api.views import SysAppRelatedViewSet


class AppMetricsMonitorViewSet(SysAppRelatedViewSet):
    """A ViewSet for interacting with app's MetricsMonitor Config"""

    model = AppMetricsMonitor
    serializer_class = AppMetricsMonitorLSZ

    def get_object(self):
        return get_object_or_404(self.get_queryset())

    @swagger_auto_schema(responses={200: AppMetricsMonitorLSZ}, request_body=AppMetricsMonitorLSZ)
    def upsert(self, request, region, name):
        try:
            instance = self.get_queryset().get()
        except AppMetricsMonitor.DoesNotExist:
            instance = None

        slz = AppMetricsMonitorLSZ(data=request.data, instance=instance)
        slz.is_valid(True)
        instance = slz.save(app=self.get_app())
        return Response(data=AppMetricsMonitorLSZ(instance).data)
