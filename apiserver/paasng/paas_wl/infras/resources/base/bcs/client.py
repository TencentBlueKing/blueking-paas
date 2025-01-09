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
from django.conf import settings

from paas_wl.infras.resources.base.bcs.apigw import Client
from paas_wl.infras.resources.base.bcs.apigw import Group as BcsGroup
from paasng.core.tenant.constants import API_HERDER_TENANT_ID


class DummyBcsClient:
    """Dummy BCS Clientwhen BCS is disabled."""

    def create_web_console_sessions(*args, **kwargs): ...


class BcsClient:
    """bcs 通过 APIGW 提供的 API"""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        client = Client(stage=settings.APIGW_ENVIRONMENT, endpoint=settings.BK_API_URL_TMPL)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        client.update_headers(self._prepare_headers())
        self.client: BcsGroup = client.api

    def _prepare_headers(self) -> dict:
        # 添加公共的 header
        return {
            API_HERDER_TENANT_ID: self.tenant_id,
            "Content-Type": "application/json",
        }

    def create_web_console_sessions(self, *args, **kwargs):
        return self.client.create_web_console_sessions(*args, **kwargs)


def get_bcs_client():
    if settings.ENABLE_BCS:
        return BcsClient
    else:
        return DummyBcsClient


bcs_client_cls = get_bcs_client()
