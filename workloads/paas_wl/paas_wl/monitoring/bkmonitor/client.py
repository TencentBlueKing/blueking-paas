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
from typing import List, Union

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from .api_resources.apigw import Client as ApigwClient
from .api_resources.apigw import Group as ApigwGroup
from .api_resources.esb import Group as ESBGroup
from .api_resources.esb import get_client_by_username
from .exceptions import BkMonitorApiError, BkMonitorGatewayServiceError

logger = logging.getLogger(__name__)


class BkMonitorClient:
    """蓝鲸监控 client"""

    def __init__(self, client: Union[ApigwGroup, ESBGroup]):
        self.client = client

    def promql_query(self, promql: str, start: str, end: str, step: str) -> List:
        """
        通过 promql 语法访问蓝鲸监控，获取容器 cpu / 内存等指标数据

        :param promql: promql 查询语句，可参考 PROMQL_TMPL
        :param start: 起始时间戳，如 "1622009400"
        :param end: 结束时间戳，如 "1622009500"
        :param step: 步长，如："1m"
        :returns: 时序数据 Series
        """

        try:
            resp = self.client.promql_query(data={'promql': promql, 'start': start, 'end': end, 'step': step})
        except APIGatewayResponseError:
            # 详细错误信息 bkapi_client_core 会自动记录
            raise BkMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if resp.get('error'):
            raise BkMonitorApiError(resp['error'])

        return resp.get('series', [])


def make_bk_monitor_client() -> BkMonitorClient:
    if settings.ENABLE_BK_MONITOR_APIGW:
        apigw_cli = ApigwClient(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_MONITOR_APIGW_SERVICE_STAGE)
        apigw_cli.update_bkapi_authorization(bk_app_code=settings.BK_APP_CODE, bk_app_secret=settings.BK_APP_SECRET)
        return BkMonitorClient(apigw_cli.api)

    # ESB 开启了免用户认证，但限制用户名不能为空，因此给默认用户名
    esb_client = get_client_by_username("admin")
    return BkMonitorClient(esb_client.monitor_v3)
