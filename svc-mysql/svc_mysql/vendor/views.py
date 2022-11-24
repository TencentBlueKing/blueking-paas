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

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from paas_service.auth.decorator import instance_authorized_require
from paas_service.models import ServiceInstance
from paas_service.utils import get_paas_app_info
from rest_framework.response import Response
from rest_framework.views import APIView
from svc_mysql.vendor.serializers import ServiceInstanceForManageSLZ

logger = logging.getLogger(__name__)


class HealthzView(APIView):
    def get(self, request):
        return Response(
            {
                "result": True,
                "data": {},
                "message": "",
            }
        )


class MySQLIndexView(TemplateView):
    template_name = "index.html"
    name = "首页"

    @method_decorator(instance_authorized_require)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        instance = get_object_or_404(ServiceInstance, pk=self.kwargs["instance_id"])
        if "view" not in kwargs:
            kwargs["view"] = self
        app_info = get_paas_app_info(instance)
        kwargs["instance"] = ServiceInstanceForManageSLZ(instance).data
        kwargs["app_info"] = app_info
        return kwargs
