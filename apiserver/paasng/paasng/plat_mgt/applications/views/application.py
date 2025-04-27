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

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.applications.serializers.application import ApplicationSLZ
from paasng.platform.applications.models import Application


class ApplicationListView(viewsets.GenericViewSet):
    """平台管理 - 应用列表 API"""

    serializer_class = ApplicationSLZ
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.applications"],
        operation_description="获取应用列表",
        responses={status.HTTP_200_OK: ApplicationSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取应用列表"""

        queryset = Application.objects.all()

        slz = self.get_serializer(queryset, many=True)
        return Response(slz.data, status=status.HTTP_200_OK)
