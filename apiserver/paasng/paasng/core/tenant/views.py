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

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.core.tenant.serializers import TenantListOutputSLZ
from paasng.core.tenant.user import get_tenant
from paasng.infras.bk_user.client import BkUserClient


class TenantViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["paasng.core.tenant"],
        operation_description="获取所有租户列表",
        responses={status.HTTP_200_OK: TenantListOutputSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        user_tenant_id = get_tenant(request.user).id
        tenants = BkUserClient(user_tenant_id).list_tenants()
        return Response(data=TenantListOutputSLZ(tenants, many=True).data)
