# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Callable

from rest_framework import permissions

from paasng.accounts.models import UserProfile

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import View

logger = logging.getLogger(__name__)


@dataclass
class HasRegionPermission(permissions.BasePermission):
    getter: Callable[['Request', 'View'], str]

    @classmethod
    def from_url_var(cls, name="region"):
        """Get region from url vars"""

        def get_region_by_url_var(request: 'Request', view: 'View') -> 'str':
            return view.kwargs[name]

        return partial(cls, getter=get_region_by_url_var)

    def has_permission(self, request: 'Request', view: 'View'):
        try:
            region = self.getter(request, view)
        except Exception:
            logger.warning("get region name failed")
            return False

        user_profile = UserProfile.objects.get_profile(request.user)
        return user_profile.enable_regions.has_region_by_name(region)
