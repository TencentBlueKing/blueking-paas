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
from django.http import Http404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.utils.views import allow_resp_patch

from .models import get_all_regions
from .serializers import RegionSerializer


class RegionBaseViewSet(viewsets.ViewSet):
    @staticmethod
    def get_region_or_404(region_name):
        regions = get_all_regions()
        if region_name not in regions:
            raise Http404("No %s matches the given query." % region_name)
        return regions[region_name]


class RegionViewSet(RegionBaseViewSet):
    """ViewSet for Regions"""

    permission_classes = [IsAuthenticated]

    @allow_resp_patch
    def retrieve(self, request, region):
        region_object = self.get_region_or_404(region)
        region_object.load_dynamic_infos()

        resp = RegionSerializer(region_object).serialize()
        return Response(resp)
