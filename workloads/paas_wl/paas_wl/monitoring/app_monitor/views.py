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
