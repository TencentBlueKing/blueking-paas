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
"""Utilities for auto generate swagger API documents
"""
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from rest_framework.request import Request

from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class

openapi_empty_schema = openapi.Schema(type='object')
openapi_empty_response = openapi.Response(_('操作成功后的空响应'), schema=openapi_empty_schema)


def is_rendering_openapi(request: Request) -> bool:
    """判断是否正在渲染 openapi 文档"""
    return (
        len(request.data) == 0
        and site_perm_class(SiteAction.VISIT_ADMIN42).has_permission(request)
        and request.accepted_media_type == 'application/openapi+json'
    )
