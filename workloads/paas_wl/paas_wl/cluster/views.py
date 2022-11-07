# -*- coding: utf-8 -*-
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
