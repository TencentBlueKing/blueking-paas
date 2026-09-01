# -*- coding: utf-8 -*-
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

"""e2b 协议端点的权限类。

协议端点不走 APIGW / 应用成员权限，认证与授权都落在 API Key 上：
认证后端负责验 key，这里再确认请求主体就是 Key 解析出的 ``E2BPrincipal``，
避免只配 ``IsAuthenticated`` 被 perm_insure 判为权限泄漏，
也避免将来误挂其他认证后端时被普通登录态放行。
"""

from rest_framework.permissions import BasePermission

from .authentication import E2BPrincipal


class IsE2BApiKey(BasePermission):
    """只放行经 e2b API Key 认证的请求。"""

    message = "Request must be authenticated with a valid e2b API key."

    def has_permission(self, request, view) -> bool:
        return isinstance(request.user, E2BPrincipal)
