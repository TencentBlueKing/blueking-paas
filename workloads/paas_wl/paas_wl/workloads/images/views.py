# -*- coding: utf-8 -*-
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
