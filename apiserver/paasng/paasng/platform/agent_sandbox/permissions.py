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

from paasng.infras.accounts.permissions.application import BaseAppPermission
from paasng.platform.applications.models import Application


class IsAPIGWVerifiedApp(BaseAppPermission):
    """校验请求是否经由 API Gateway 转发，且来源应用已通过认证。"""

    message = "Request must come from API Gateway with a verified app."

    def has_permission(self, request, view) -> bool:
        """检查请求中是否携带经网关认证的应用信息（request.app 由 ApiGatewayJWTAppMiddleware 注入）。如果未携带，则没有权限。"""
        app = getattr(request, "app", None)
        if not app:
            return False
        return bool(app.verified)

    def has_object_permission(self, request, view, obj: Application) -> bool:
        """检查请求来源应用是否与目标应用一致，如果不一致，则没有权限。"""
        app = getattr(request, "app", None)
        if not app:
            return False
        return app.bk_app_code == obj.code
