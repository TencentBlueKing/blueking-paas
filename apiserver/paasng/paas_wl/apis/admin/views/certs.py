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

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from paas_wl.workloads.networking.ingress.models import AppDomainSharedCert
from paas_wl.workloads.networking.ingress.serializers import AppDomainSharedCertSLZ, UpdateAppDomainSharedCertSLZ
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record


class AppDomainSharedCertsViewSet(ModelViewSet):
    """A viewSet for managing app certificates"""

    lookup_field = "name"
    model = AppDomainSharedCert
    serializer_class = AppDomainSharedCertSLZ
    pagination_class = None
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    queryset = AppDomainSharedCert.objects.all()

    @transaction.atomic
    def update(self, request, name):
        """Update a shared certificate"""
        cert = get_object_or_404(AppDomainSharedCert, name=name)
        data_before = DataDetail(data=AppDomainSharedCertSLZ(cert).data)

        serializer = UpdateAppDomainSharedCertSLZ(cert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # TODO: Find all appdomain which is using this certificate, refresh their secret resources

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.SHARED_CERT,
            attribute=name,
            data_before=data_before,
            data_after=DataDetail(data=AppDomainSharedCertSLZ(cert).data),
        )
        return Response(self.serializer_class(cert).data)

    def create(self, request, *args, **kwargs):
        """Create a shared certificate"""
        serializer = AppDomainSharedCertSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.SHARED_CERT,
            attribute=serializer.data["name"],
            data_after=DataDetail(data=serializer.data),
        )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete a shared certificate"""
        cert = self.get_object()
        data_before = DataDetail(data=AppDomainSharedCertSLZ(cert).data)
        cert.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.SHARED_CERT,
            attribute=cert.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
