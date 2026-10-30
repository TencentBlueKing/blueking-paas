# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""API 层共用的快捷函数，类似 ``django.shortcuts``：把各路由里重复的「取对象，取不到就 404」收在一处。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import aget_object_or_404

from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.infras.accounts.auth import authenticated_user

if TYPE_CHECKING:
    from django.http import HttpRequest


async def aget_project_or_404(request: HttpRequest, project_id: str) -> Project:
    """取当前用户可见的 Project，不可见就抛 404。

    「可见」目前就是自己 owner、同租户、未删除。不存在、已删除、别人的、别的租户的项目一律给出
    相同的 404，不暴露它是否存在。

    :param request: 已登录的请求。
    :param project_id: 路径里的项目 ID。
    :return: 当前用户可见的 Project。
    :raises Http404: Project 对当前用户不可见。

    用法::

        project = await aget_project_or_404(request, project_id)
    """
    user = authenticated_user(request)
    return await aget_object_or_404(
        Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id),
        id=project_id,
    )
