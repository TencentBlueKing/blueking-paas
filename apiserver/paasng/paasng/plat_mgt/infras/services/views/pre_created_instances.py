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

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from paasng.accessories.services.models import Plan, PreCreatedInstance, Service
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.infras.services.serializers import PlanWithPreCreatedInstanceSLZ, PreCreatedInstanceSLZ


class PreCreatedInstanceViewSet(ModelViewSet):
    """（平台管理）增强服务资源池相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    schema = None
    serializer_class = PreCreatedInstanceSLZ
    lookup_field = "uuid"

    def get_plan(self):
        return Plan.objects.get(pk=self.kwargs["plan_id"])

    def get_queryset(self):
        qs = PreCreatedInstance.objects.all()
        if "plan_id" in self.kwargs:
            qs.filter(plan=self.get_plan())
        return qs.order_by("created")

    def list(self, request, *args, **kwargs):
        qs = Plan.objects.filter(
            service__in=[service for service in Service.objects.all() if service.config.get("provider_name") == "pool"]
        )
        page = self.paginate_queryset(qs)
        return Response(PlanWithPreCreatedInstanceSLZ(page or qs, many=True).data)
