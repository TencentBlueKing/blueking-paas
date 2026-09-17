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

"""查询开发者中心在权限中心 V4 上的系统认证令牌

该令牌只用于校验权限中心回调平台资源接口时携带的 Basic 凭证，不参与主动鉴权调用。
"""

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient


def fetch_system_token(tenant_id: str) -> str:
    """取开发者中心在权限中心 V4 上的系统认证令牌"""
    client = BKIAMV4BaseClient(tenant_id)

    resp = client.call(
        client.client.retrieve_system_auth_token,
        path_params={"system_id": get_paas_system_id()},
        for_write=False,
    )

    # 基座只校验响应顶层，data 是列表或字符串时直接 .get 会抛 AttributeError，
    # 绕过调用方的异常收敛把回调打成 500
    data = resp.get("data")
    if not isinstance(data, dict):
        raise BKIAMGatewayServiceError("bkiam api retrieve_system_auth_token returned non-object data")

    # 空串会与不带密码的 Basic 凭证比中，把认证失败变成认证通过
    token = data.get("auth_token")
    if not token or not isinstance(token, str):
        raise BKIAMGatewayServiceError("bkiam api retrieve_system_auth_token returned no auth_token")

    return token
