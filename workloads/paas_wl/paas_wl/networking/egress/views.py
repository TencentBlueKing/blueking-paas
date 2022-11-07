# -*- coding: utf-8 -*-
import logging

from django.db import transaction
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from paas_wl.cluster.models import Cluster
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.misc import get_cluster_egress_ips
from paas_wl.networking.egress.models import RCStateAppBinding, RegionClusterState
from paas_wl.networking.egress.serializers import RCStateAppBindingSLZ
from paas_wl.platform.applications.models.config import Config
from paas_wl.platform.system_api.views import SysAppRelatedViewSet, SysViewSet
from paas_wl.utils.error_codes import error_codes

logger = logging.getLogger()


class RCStateBindingsViewSet(SysAppRelatedViewSet):
    """A viewset for interacting with RCStateBindings"""

    @transaction.atomic
    def create(self, request, region, name):
        """Create a new RCStateBinding relationship"""
        app = self.get_app()
        cluster = get_cluster_by_app(app)
        try:
            state = RegionClusterState.objects.filter(region=app.region, cluster_name=cluster.name).latest()
            binding = RCStateAppBinding.objects.create(app=app, state=state)
        except RegionClusterState.DoesNotExist:
            raise error_codes.CREATE_RCSTATE_BINDING_ERROR.f(f"region {app.region} 没有集群状态信息")
        except IntegrityError:
            raise error_codes.CREATE_RCSTATE_BINDING_ERROR.f("不能重复绑定")
        except Exception:
            logger.exception('Unable to crate RCStateBinding instance')
            raise error_codes.CREATE_RCSTATE_BINDING_ERROR.f("未知错误")

        serializer = RCStateAppBindingSLZ(binding)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request, region, name):
        """Remove an established RCStateBinding relationship"""
        app = self.get_app()
        binding = get_object_or_404(RCStateAppBinding, app=app)
        binding.delete()

        # Update app scheduling config
        # TODO: Below logic is safe be removed as long as the node_selector will be fetched
        # dynamically by querying for binding state.
        latest_config = Config.objects.filter(app=app).latest()
        # Remove labels related with current binding
        for key in binding.state.to_labels():
            latest_config.node_selector.pop(key, None)
        latest_config.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterEgressViewSet(SysViewSet):
    """A viewset for managing egress configs for cluster"""

    def retrieve(self, request, region, name):
        """Get cluster's egress info"""
        cluster = get_object_or_404(Cluster, region=region, name=name)
        result = get_cluster_egress_ips(cluster)
        return Response(result)
