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
import cattrs
from bkapi_client_core.exceptions import APIGatewayResponseError

from paasng.bk_plugins.pluginscenter.bk_user.backend.esb import get_client_by_username
from paasng.bk_plugins.pluginscenter.bk_user.definitions import DepartmentDetail
from paasng.bk_plugins.pluginscenter.bk_user.exceptions import BkUserManageApiError, BkUserManageGatewayServiceError


class BkUserManageClient:
    def __init__(self):
        # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
        self.client = get_client_by_username("admin").api

    def retrieve_department(self, department_id: int) -> DepartmentDetail:
        try:
            resp = self.client.retrieve_department(params={"id": department_id})
        except APIGatewayResponseError:
            raise BkUserManageGatewayServiceError("Failed to list custom collector config")

        if not resp["result"]:
            raise BkUserManageApiError(resp["message"])

        data = resp["data"]
        return cattrs.structure(data, DepartmentDetail)
