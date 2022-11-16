# -*- coding: utf-8 -*-
from typing import Optional

from drf_yasg.utils import swagger_auto_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, mixins

from paas_wl.admin.serializers.clusters import APIServerSLZ, ClusterRegisterRequestSLZ, ReadonlyClusterSLZ
from paas_wl.cluster.models import APIServer, Cluster
from paas_wl.platform.applications.permissions import SiteAction, site_perm_class


class ClusterViewSet(mixins.DestroyModelMixin, ReadOnlyModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ReadonlyClusterSLZ
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['region', 'name', 'is_default']
    ordering = ('-region',)
    ordering_fields = ('region', 'created', 'updated')

    @swagger_auto_schema(request_body=ClusterRegisterRequestSLZ)
    def update_or_create(self, request, pk: Optional[str] = None):
        slz = ClusterRegisterRequestSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        cluster = Cluster.objects.register_cluster(**data)
        return Response(data=ReadonlyClusterSLZ(cluster).data)

    @swagger_auto_schema(request_body=APIServerSLZ)
    def bind_api_server(self, request, pk):
        slz = APIServerSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        cluster = self.get_object()
        api_server, _ = APIServer.objects.update_or_create(
            cluster=cluster, host=data["host"], defaults=dict(overridden_hostname=data["overridden_hostname"])
        )
        return Response(data=APIServerSLZ(api_server).data)

    def unbind_api_server(self, request, pk, api_server_id):
        cluster = self.get_object()
        APIServer.objects.filter(cluster=cluster, uuid=api_server_id).delete()
        return Response()
