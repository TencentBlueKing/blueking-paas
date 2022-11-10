# -*- coding: utf-8 -*-
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from paas_wl.networking.ingress.models import AppDomainSharedCert
from paas_wl.networking.ingress.serializers import AppDomainSharedCertSLZ, UpdateAppDomainSharedCertSLZ
from paas_wl.platform.applications.permissions import site_perm_class


class AppDomainSharedCertsViewSet(ModelViewSet):
    """A viewSet for managing app certificates"""

    lookup_field = 'name'
    model = AppDomainSharedCert
    serializer_class = AppDomainSharedCertSLZ
    pagination_class = None
    permission_classes = [site_perm_class("admin:manage:workloads")]
    queryset = AppDomainSharedCert.objects.all()

    @transaction.atomic
    def update(self, request, name):
        """Update a shared certificate"""
        cert = get_object_or_404(AppDomainSharedCert, name=name)
        serializer = UpdateAppDomainSharedCertSLZ(cert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # TODO: Find all appdomain which is using this certificate, refresh their secret resources
        return Response(self.serializer_class(cert).data)
