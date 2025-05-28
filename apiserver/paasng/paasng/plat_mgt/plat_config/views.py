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

from django.conf import settings as django_settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class

from .serializers import UserListFeaturesSlz


class PlatMgtFrontendFeatureViewSet(viewsets.GenericViewSet):
    """平台管理前端特性配置 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.plat_config"],
        operation_description="获取平台管理前端特性配置",
        responses={status.HTTP_200_OK: None},
    )
    def list_frontend_features(self, request):
        """获取平台管理前端特性配置"""
        # 平台管理页面的前端特性配置
        features = {
            # 是否显示用户列表，当 AUTO_CREATE_REGULAR_USER 为 False 时显示
            "SHOW_USER_LIST": not django_settings.AUTO_CREATE_REGULAR_USER,
        }
        return Response(features)

    @swagger_auto_schema(
        tags=["plat_mgt.plat_config"],
        operation_description="获取平台管理前端特性配置",
        request_body=UserListFeaturesSlz,
        responses={status.HTTP_200_OK: None},
    )
    def update_frontend_features(self, request):
        """更新平台管理前端特性配置"""

        slz = UserListFeaturesSlz(data=request.data)
        slz.is_valid(raise_exception=True)
        show_user_list = slz.validated_data["show_user_list"]

        auto_create_regular_user = not show_user_list
        setattr(django_settings, "AUTO_CREATE_REGULAR_USER", auto_create_regular_user)

        return Response(
            {
                "show_user_list": show_user_list,
            },
            status=status.HTTP_200_OK,
        )
