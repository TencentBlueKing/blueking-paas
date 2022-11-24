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
from rest_framework import status
from rest_framework.response import Response

from paas_wl.platform.system_api.views import SysViewSet

from .models import AppModelResource, create_app_resource
from .serializers import AppModelResourceSerializer, CreateAppModelResourceSerializer


class AppModelResourceViewSet(SysViewSet):
    def create(self, request, region: str):
        """Create the AppModelResource object for Module"""
        serializer = CreateAppModelResourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        resource = create_app_resource(
            # Use Application code as default resource name
            name=d['code'],
            image=d['image'],
            command=d.get('command'),
            args=d.get('args'),
            target_port=d.get('target_port'),
        )
        model_resource = AppModelResource.objects.create_from_resource(
            region, d['application_id'], d['module_id'], resource
        )
        return Response(AppModelResourceSerializer(model_resource).data, status=status.HTTP_201_CREATED)
