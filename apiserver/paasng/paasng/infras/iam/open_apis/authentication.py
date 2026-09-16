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

import logging

from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_system_token

logger = logging.getLogger(__name__)

# 权限中心回调时固定使用的用户名，密码为开发者中心的系统认证令牌
IAM_CALLBACK_USERNAME = "bk_iam"


class IAMBasicAuthentication(BasicAuthentication):
    """对权限中心回调平台资源接口的请求做认证

    两个版本的凭证形式一致，均为 Basic base64(bk_iam:{system_token})，取令牌的方式
    由 shim 按 BK_IAM_VERSION 分发。

    note: 失败一律抛 DRF 的 AuthenticationFailed，由全局异常处理器转成 401。
        此处不可换成自定义异常类型，那样会落到兜底分支变成 500
    """

    def authenticate(self, request):
        result = super().authenticate(request)

        # 未携带 Authorization 头时 DRF 返回 None，表示「本认证类不处理该请求」。
        # 该视图的 permission_classes 为空，放过去等同于匿名放行，必须在此拦下
        if result is None:
            raise AuthenticationFailed("basic auth credentials were not provided")

        return result

    def authenticate_credentials(self, userid: str, password: str, request=None):
        if userid != IAM_CALLBACK_USERNAME:
            raise AuthenticationFailed(f"username is not {IAM_CALLBACK_USERNAME}")

        # 令牌由平台反过来向权限中心查询。认证发生在视图之前，取不到请求里的租户头，
        # 而令牌本身是系统级的，故固定用初始租户查询
        try:
            token = get_system_token(get_init_tenant_id())
        except BKIAMGatewayServiceError as e:
            # 取不到令牌就无从比对，与凭证不符同样按认证失败处理：权限中心据此重试即可，
            # 返回 5xx 反而会被当成平台故障
            logger.warning("fetch system token for iam callback failed: %s", e)
            raise AuthenticationFailed("failed to fetch system token")

        if password != token:
            raise AuthenticationFailed("password in basic_auth not equals to system token")

        return ({"username": userid, "password": password}, None)
