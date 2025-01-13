# -*- coding: utf-8 -*-
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

import logging
from contextlib import contextmanager
from typing import List

import cattrs
from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.core.tenant.constants import API_HERDER_TENANT_ID
from paasng.infras.bk_user import entities
from paasng.infras.bk_user.apigw.client import Client
from paasng.infras.bk_user.apigw.client import Group as BkUserGroup
from paasng.infras.bk_user.exceptions import BkUserGatewayServiceError

logger = logging.getLogger(__name__)


@contextmanager
def wrap_request_exc():
    try:
        yield
    except (APIGatewayResponseError, ResponseError) as e:
        raise BkUserGatewayServiceError("call bk-user api error, detail: {}".format(e))


class BkUserClient:
    """用户管理通过 APIGW 提供的 API"""

    def __init__(self, tenant_id: str, stage: str = "prod"):
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=stage)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers({API_HERDER_TENANT_ID: tenant_id})
        self.client: BkUserGroup = client.api

    def list_tenants(self) -> List[entities.Tenant]:
        """获取租户列表"""
        with wrap_request_exc():
            resp = self.client.list_tenants()

        return cattrs.structure(resp["data"], List[entities.Tenant])
