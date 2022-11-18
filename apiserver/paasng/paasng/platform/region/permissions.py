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

from rest_framework import permissions

from paasng.accounts.models import UserProfile
from paasng.utils.api_docs import is_rendering_openapi


class HasPostRegionPermission(permissions.BasePermission):
    """
    check post request
    """

    def has_permission(self, request, view):
        # only check post request, let other requests go
        if request.method != 'POST':
            return True

        # 如果在渲染 openapi 文档, 那么跳过权限校验.
        if is_rendering_openapi(request):
            return True

        try:
            region = request.data['region']
        except KeyError:
            return False

        user_profile = UserProfile.objects.get_profile(request.user)
        return user_profile.enable_regions.has_region_by_name(region)
