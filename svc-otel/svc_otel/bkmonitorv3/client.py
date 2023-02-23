# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import Dict

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from svc_otel.bkmonitorv3.backend.apigw import Client
from svc_otel.bkmonitorv3.backend.esb import get_client_by_username
from svc_otel.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError
from typing_extensions import Protocol

logger = logging.getLogger(__name__)


class BkMonitorBackend(Protocol):
    """Describes protocols of calling API service"""

    def create_apm_application(self, *args, **kwargs) -> Dict:
        ...


class BkMonitorClient:
    """API provided by BK Monitor

    :param backend: client 后端实际的 backend
    """

    def __init__(
        self,
        backend: BkMonitorBackend,
    ):
        self.client = backend

    def create_apm(self, apm_name: str, bk_monitor_space_id: str) -> str:
        """创建 APM 应用，返回 data_token

        OTEL 的返回数据格式：
        {
            "result": true,
            "code": 200,
            "message": "OK",
            "data": "xxxxxxx",
            "request_id": "d29570cab0d447529d53cc192df25157"
        }

        {
            "result": false,
            "message": "应用名称已存在",
            "data": {},
            "code": 500,
            "request_id": "a06f6c1a66c34d0a880186759fec0d06"
        }
        """
        # 在指定的命名空间下创建 APM 应用
        data = {"app_name": apm_name, "space_uid": bk_monitor_space_id}
        try:
            resp = self.client.apm_create_application(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError("Failed to create APM on BK Monitor") from e

        if not resp['result']:
            logger.error(
                f'Failed to create APM BK Monitor, resp:{resp} \apm_name: {apm_name}, space_uid:{bk_monitor_space_id}'
            )
            raise BkMonitorApiError(resp['message'])
        return resp['data']


def make_bk_monitor_client() -> BkMonitorClient:
    if settings.ENABLE_BK_MONITOR_APIGW:
        apigw_client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.APIGW_ENVIRONMENT)
        apigw_client.update_bkapi_authorization(
            **{
                'bk_app_code': settings.BK_APP_CODE,
                'bk_app_secret': settings.BK_APP_SECRET,
            }
        )
        return BkMonitorClient(apigw_client.api)

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return BkMonitorClient(esb_client.monitor_v3)
