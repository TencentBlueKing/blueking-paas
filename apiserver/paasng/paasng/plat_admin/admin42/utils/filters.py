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

from functools import reduce
from operator import or_

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.models import user_id_encoder
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.plat_admin.admin42.serializers.accountmgr import UserProfileQueryParamSLZ
from paasng.plat_admin.admin42.serializers.application import ApplicationFilterSLZ
from paasng.platform.applications.models import Application, BaseApplicationFilter


class ApplicationFilterBackend(BaseFilterBackend):
    """应用过滤器
    使用场景：应用资源方案（普通应用可以在 Admin42 页面上调整）
    """

    def filter_queryset(self, request, queryset, view):
        if queryset.model != Application:
            raise ValueError("ApplicationFilterBackend only support to filter Application")

        # 校验 filter 参数
        query_slz = ApplicationFilterSLZ(data=request.query_params)
        query_slz.is_valid(raise_exception=True)
        query_params = query_slz.data

        return BaseApplicationFilter.filter_queryset(queryset=queryset, **query_params)


class UserProfileFilterBackend(BaseFilterBackend):
    """用户信息列表过滤器"""

    def filter_queryset(self, request, queryset, view):
        if queryset.model != UserProfile:
            raise ValueError("UserProfileFilterBackend only support to filter UserProfile")
        slz = UserProfileQueryParamSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        if not slz.validated_data["display_regular_users"]:
            queryset = queryset.exclude(role=SiteRole.USER.value)

        if slz.validated_data["filter_key"]:
            op = reduce(
                or_,
                [
                    Q(user__startswith=user_id_encoder.encode(type_, slz.validated_data["filter_key"]))
                    for type_ in ProviderType
                ],
            )
            queryset = queryset.filter(op)

        return queryset
