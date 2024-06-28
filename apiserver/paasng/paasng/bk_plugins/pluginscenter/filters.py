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

from rest_framework.filters import BaseFilterBackend

from paasng.bk_plugins.pluginscenter.constants import PluginStatus
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.client import lazy_iam_client
from paasng.bk_plugins.pluginscenter.models import PluginInstance


class PluginInstancePermissionFilter(BaseFilterBackend):
    """PluginPermissionFilter will filter those PluginInstance own by the request.user"""

    def filter_queryset(self, request, queryset, view):
        # skip filter if queryset is not for PluginInstance
        if queryset.model is not PluginInstance:
            return queryset

        # 创建未审批中插件的未接入权限中心，仅创建者可在列表页面查看
        approval_qs = queryset.model.objects.filter(creator=request.user.pk, status__in=PluginStatus.approval_status())

        filters = lazy_iam_client.build_plugin_filters(username=request.user.username)
        if filters:
            return queryset.filter(filters) | approval_qs
        else:
            return approval_qs
