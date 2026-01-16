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
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.platform.bkapp_model.models import ResQuotaPlan

from .serializers import ResQuotaPlanSLZ


class ResQuotaPlanOptionsView(APIView):
    """资源配额方案 选项视图"""

    @swagger_auto_schema(response_serializer=ResQuotaPlanSLZ(many=True))
    def get(self, request):
        return Response(
            data=ResQuotaPlanSLZ(
                [
                    {
                        "name": plan_obj.name,
                        "limit": plan_obj.limits,
                        "request": plan_obj.requests,
                    }
                    for plan_obj in ResQuotaPlan.objects.filter(is_active=True)
                ],
                many=True,
            ).data
        )
