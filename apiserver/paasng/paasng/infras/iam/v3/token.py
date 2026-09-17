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

"""查询开发者中心在权限中心 V3 上的系统认证令牌

该令牌只用于校验权限中心回调平台资源接口时携带的 Basic 凭证，不参与主动鉴权调用。
"""

from django.conf import settings
from iam import IAM

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id


def fetch_system_token(tenant_id: str) -> str:
    """取开发者中心在权限中心 V3 上的系统认证令牌"""
    _iam = IAM(
        settings.IAM_APP_CODE,
        settings.IAM_APP_SECRET,
        settings.BK_IAM_APIGATEWAY_URL,
        bk_tenant_id=tenant_id,
    )

    ok, msg, token = _iam.get_token(get_paas_system_id())

    # SDK 以返回值而非异常表达失败，收敛成与 V4 一致的异常，让调用方只认一种失败形态
    if not ok:
        raise BKIAMGatewayServiceError(f"get system token from bkiam v3 failed: {msg}")

    # ok 为真不代表拿到了令牌：SDK 取字段带了默认值，缺 token 键时返回空串。
    # 空串会与不带密码的 Basic 凭证比中，把认证失败变成认证通过
    if not token or not isinstance(token, str):
        raise BKIAMGatewayServiceError("bkiam v3 api get_token returned no token")

    return token
