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
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.applications.permissions import AppAction, application_perm_class
from paas_wl.platform.applications.views import ApplicationCodeInPathMixin
from paas_wl.platform.auth.views import BaseEndUserViewSet
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.images.models import AppUserCredential
from paas_wl.workloads.images.serializers import UsernamePasswordPairSLZ


class AppUserCredentialViewSet(ApplicationCodeInPathMixin, BaseEndUserViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: UsernamePasswordPairSLZ(many=True)})
    def list(self, request, code):
        """list all username password pair"""
        application = self.get_application()

        instances = AppUserCredential.objects.filter(application_id=application.id).order_by("created")
        return Response(data=UsernamePasswordPairSLZ(instances, many=True).data)

    @swagger_auto_schema(responses={201: UsernamePasswordPairSLZ()}, request_body=UsernamePasswordPairSLZ)
    def create(self, request, code):
        """create a username password pair"""
        application = self.get_application()

        slz = UsernamePasswordPairSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        try:
            instance = slz.save(application_id=application.id)
        except IntegrityError:
            raise error_codes.CREATE_CREDENTIALS_FAILED.f(_("同名凭证已存在"))
        return Response(data=UsernamePasswordPairSLZ(instance).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={200: UsernamePasswordPairSLZ()}, request_body=UsernamePasswordPairSLZ)
    def update(self, request, code, name):
        """update a username password pair"""
        application = self.get_application()

        instance = get_object_or_404(AppUserCredential, application_id=application.id, name=name)
        slz = UsernamePasswordPairSLZ(data=request.data, instance=instance)
        slz.is_valid(raise_exception=True)
        updated = slz.save()
        return Response(data=UsernamePasswordPairSLZ(updated).data, status=status.HTTP_200_OK)

    def destroy(self, request, code, name):
        """delete a username password pair"""
        application = self.get_application()

        instance = get_object_or_404(AppUserCredential, application_id=application.id, name=name)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
