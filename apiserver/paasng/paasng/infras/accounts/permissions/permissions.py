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
import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Callable

from rest_framework import permissions

from paasng.infras.accounts.models import UserProfile
from paasng.utils.api_docs import is_rendering_openapi

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import View

logger = logging.getLogger(__name__)


@dataclass
class HasRegionPermission(permissions.BasePermission):
    getter: Callable[["Request", "View"], str]

    @classmethod
    def from_url_var(cls, name="region"):
        """Get region from url vars"""

        def get_region_by_url_var(request: "Request", view: "View") -> "str":
            return view.kwargs[name]

        return partial(cls, getter=get_region_by_url_var)

    def has_permission(self, request: "Request", view: "View"):
        try:
            region = self.getter(request, view)
        except Exception:
            logger.warning("get region name failed")
            return False

        user_profile = UserProfile.objects.get_profile(request.user)
        return user_profile.enable_regions.has_region_by_name(region)


class HasPostRegionPermission(permissions.BasePermission):
    """Check if the current user has the permission to perform POST request in the current region."""

    def has_permission(self, request, view):
        # only check post request, let other requests go
        if request.method != "POST":
            return True

        # 如果在渲染 openapi 文档, 那么跳过权限校验.
        if is_rendering_openapi(request):
            return True

        try:
            region = request.data["region"]
        except KeyError:
            return False

        user_profile = UserProfile.objects.get_profile(request.user)
        return user_profile.enable_regions.has_region_by_name(region)
