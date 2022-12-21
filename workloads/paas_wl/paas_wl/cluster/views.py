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
from dataclasses import asdict

from django.http import Http404
from rest_framework.response import Response

from paas_wl.cluster.models import Cluster
from paas_wl.networking.ingress.config import get_custom_domain_config
from paas_wl.platform.system_api.views import SysViewSet

from .serializers import ClusterSLZ

logger = logging.getLogger()


class RegionClustersViewSet(SysViewSet):
    """A Viewset for viewing and managing clusters"""

    def list(self, request, region):
        """List clusters under a region"""
        qs = Cluster.objects.filter(region=region)
        if not qs.exists():
            raise Http404

        data = ClusterSLZ(qs.all(), many=True).data
        return Response(data)


class RegionSettingsViewSet(SysViewSet):
    """Check all region-aware level settings"""

    def retrieve(self, request, region):
        """Get region settings"""
        return Response({'custom_domain': asdict(get_custom_domain_config(region))})
