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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.auth.permissions import IsInternalAdmin
from paas_wl.platform.system_api.views import SysAppRelatedViewSet
from paas_wl.workloads.images import serializers
from paas_wl.workloads.images.models import AppImageCredential


class AppImageCredentialsViewSet(SysAppRelatedViewSet):
    model = AppImageCredential
    serializer_class = serializers.AppImageCredentialSerializer
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def upsert(self, request, region, name):
        app = self.get_app()
        slz = serializers.AppImageCredentialSerializer(data=request.data)
        slz.is_valid(True)

        data = slz.validated_data
        instance, _ = AppImageCredential.objects.update_or_create(
            app=app, registry=data["registry"], defaults={"username": data["username"], "password": data["password"]}
        )
        return Response(data=serializers.AppImageCredentialSerializer(instance).data)
