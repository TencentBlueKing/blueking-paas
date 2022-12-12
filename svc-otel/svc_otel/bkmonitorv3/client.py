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

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from svc_otel.bkmonitorv3.apigw.client import Client
from svc_otel.bkmonitorv3.apigw.client import Group as BkMonitorGroup
from svc_otel.bkmonitorv3.esb.client import get_client_by_username
from svc_otel.bkmonitorv3.exceptions import BkMonitorApiError, BkMonitorGatewayServiceError, BkMonitorSpaceDoesNotExist

logger = logging.getLogger(__name__)


class BkMonitorClient:
    def __init__(self):
        # 空间类型ID，默认default,允许：bkcc, bcs, bkci, paas，由蓝鲸监控侧内置分配
        self.space_type_id = "paas"

    def get_or_create_space(self, app_code: str, app_name: str, operator: str):
        try:
            space_uid = self._get_space_detail(app_code)
        except BkMonitorSpaceDoesNotExist:
            space_uid = self._create_space(app_code, app_name, operator)

        return space_uid

    def _get_space_detail(self, app_code: str) -> str:
        """获取空间详情"""
        try:
            resp = self.client.metadata_get_space_detail({"space_type_id": self.space_type_id, "space_id": app_code})
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError(f'Failed to get app space detail on BK Monitor, {e}')

        # TODO 目前监控的API返回值只有 true 和 false，没有更详细的错误码来确定是否空间已经存在
        # 等监控侧优化后，可以改为根据错误码来判断空间是否不存在
        if not resp.get('result'):
            logger.exception(f'Failed to get app({app_code}) space detail on BK Monitor, resp:{resp}')
            raise BkMonitorSpaceDoesNotExist(resp['message'])

        return resp.get('data', {}).get('space_uid')

    def _create_space(self, app_code: str, app_name: str, operator: str) -> str:
        """在蓝鲸监控上创建应用对应的空间"""
        data = {
            "space_name": app_name,
            "space_id": app_code,
            "space_type_id": self.space_type_id,
            "creator": operator,
        }
        try:
            resp = self.client.metadata_create_space(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError(f'Failed to create app space on BK Monitor, {e}')

        if not resp.get('result'):
            logger.exception(f'Failed to create app space on BK Monitor, resp:{resp} \ndata: {data}')
            raise BkMonitorApiError(resp['message'])

        return resp.get('data', {}).get('space_uid')

    def create_apm_application(self, apm_name: str, bk_monitor_space_id: str) -> str:
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
        try:
            resp = self.client.apm_create_application({"app_name": apm_name, "space_uid": bk_monitor_space_id})
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError(f"Failed to create APM on BK Monitor, {e}")

        if not resp['result']:
            logger.exception(
                f'Failed to create APM BK Monitor, resp:{resp} \apm_name: {apm_name}, space_uid:{bk_monitor_space_id}'
            )
            raise BkMonitorApiError(resp['message'])
        return resp['data']


class BkMonitorClientByApiGw(BkMonitorClient):
    """蓝鲸监控通过 APIGW 提供的 API"""

    def __init__(self):
        super().__init__()

        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.APIGW_ENVIRONMENT)
        client.update_bkapi_authorization(
            **{
                'bk_app_code': settings.BK_APP_CODE,
                'bk_app_secret': settings.BK_APP_SECRET,
            }
        )
        self.client: BkMonitorGroup = client.api


class BkMonitorClientByEsb(BkMonitorClient):
    """蓝鲸监控通过 ESB 提供的 API"""

    def __init__(self):
        super().__init__()
        # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
        client = get_client_by_username("admin")
        self.client = client.monitor_v3


def make_bk_monitor_client():
    if settings.ENABLE_BK_MONITOR_APIGW:
        return BkMonitorClientByApiGw()
    else:
        return BkMonitorClientByEsb()
