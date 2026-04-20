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

import string

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.platform.applications.models import ReservedPrefixAuthCode
from paasng.utils.error_codes import error_codes

from .serializers import AuthCodeListInputSLZ, AuthCodeOutputSLZ, GenAuthCodeInputSLZ

# 授权码字符生成范围和长度
RESERVED_PREFIX_AUTH_CODE_CHARS = string.ascii_uppercase + string.digits
RESERVED_PREFIX_AUTH_CODE_LENGTH = 8


class ReservedPrefixAuthCodeViewSet(viewsets.GenericViewSet):
    """保留前缀授权码管理接口"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]
    queryset = ReservedPrefixAuthCode.objects.all().order_by("-created")

    @swagger_auto_schema(
        tags=["平台管理-保留前缀授权码"],
        operation_description="获取授权码列表",
        responses={status.HTTP_200_OK: ""},
    )
    def list(self, request):
        """获取授权码列表"""
        slz = AuthCodeListInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        search = slz.validated_data.get("search")

        queryset = self.get_queryset()
        if search:
            queryset = queryset.filter(app_code__icontains=search) | queryset.filter(auth_code__icontains=search)

        return Response(AuthCodeOutputSLZ(queryset, many=True).data)

    @swagger_auto_schema(
        tags=["平台管理-保留前缀授权码"],
        operation_description="生成授权码",
        responses={status.HTTP_201_CREATED: ""},
    )
    def create(self, request):
        """生成授权码"""
        slz = GenAuthCodeInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        app_code = slz.validated_data["app_code"]

        auth_code = get_random_string(RESERVED_PREFIX_AUTH_CODE_LENGTH, RESERVED_PREFIX_AUTH_CODE_CHARS)
        try:
            ReservedPrefixAuthCode.objects.create(
                app_code=app_code,
                auth_code=auth_code,
                creator=request.user.pk,
            )
        except IntegrityError:
            raise error_codes.CANNOT_CREATE_RESERVED_PREFIX_AUTH_CODE.f(_("应用 ID 已存在授权码"))

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.RESERVED_PREFIX_AUTH_CODE,
            app_code=app_code,
            data_after=DataDetail(data={"app_code": app_code, "auth_code": auth_code}),
        )

        return Response({"auth_code": auth_code}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["平台管理-保留前缀授权码"],
        operation_description="删除授权码",
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def destroy(self, request, id):
        """删除授权码"""
        auth_code = get_object_or_404(ReservedPrefixAuthCode, id=id)

        if auth_code.is_used:
            raise error_codes.CANNOT_DELETE_USED_RESERVED_PREFIX_AUTH_CODE.f(_("已使用的保留前缀授权码不能被删除"))

        data_before = {"app_code": auth_code.app_code, "auth_code": auth_code.auth_code}

        auth_code.delete()

        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.RESERVED_PREFIX_AUTH_CODE,
            app_code=auth_code.app_code,
            data_before=DataDetail(data=data_before),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
