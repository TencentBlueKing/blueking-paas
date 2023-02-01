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
from rest_framework.permissions import BasePermission


class IsPluginCreator(BasePermission):
    """判断是否为插件创建者"""

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user.pk


class PluginCenterFeaturePermission(BasePermission):
    """是否允许用户访问插件开发者中心"""

    def has_permission(self, request, view):
        # 原则上不希望引用开发者中心的资源
        from paasng.accounts.constants import AccountFeatureFlag as AFF
        from paasng.accounts.models import AccountFeatureFlag

        return AccountFeatureFlag.objects.has_feature(request.user, AFF.ALLOW_PLUGIN_CENTER)
