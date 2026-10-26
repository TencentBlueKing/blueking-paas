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

"""生成权限中心 V4 的无权限申请链接"""

from typing import TYPE_CHECKING, Dict, List

from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient

if TYPE_CHECKING:
    from paasng.infras.iam.permissions.request import ActionResourcesRequest


def fetch_apply_url(tenant_id: str, action_request_list: List["ActionResourcesRequest"]) -> str:
    """按操作与资源实例向权限中心 V4 申请一条无权限申请链接

    :raises BKIAMGatewayServiceError: 未能从权限中心取得申请链接
    """
    client = BKIAMV4BaseClient(tenant_id)
    resp = client.call(
        client.client.generate_perm_apply_url,
        data={
            "system_id": get_paas_system_id(),
            "permissions": [_to_permission(req) for req in action_request_list],
        },
    )

    data = resp.get("data")
    url = data.get("url") if isinstance(data, dict) else None
    if not url or not isinstance(url, str):
        raise BKIAMGatewayServiceError("bkiam api generate_perm_apply_url returned no url")
    return url


def _to_permission(req: "ActionResourcesRequest") -> Dict:
    permission: Dict = {"action_id": req.action_id}
    # 应用是顶层资源，没有祖先，因此不传 ancestors；资源无关的操作不传 resources
    if req.resources:
        permission["resources"] = [{"id": res_id, "type": req.resource_type} for res_id in req.resources]
    return permission
