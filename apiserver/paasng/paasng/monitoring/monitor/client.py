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
from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property
from django.conf import settings


class Group(OperationGroup):
    # 查询告警
    search_alert = bind_property(
        Operation,
        name='search_alert',
        method='POST',
        path='/search_alert/',
    )


class BKMonitorClient(APIGatewayClient):
    """蓝鲸监控提供的网关 client"""

    _api_name = 'bkmonitorv3'
    api = bind_property(Group, name='api')


def make_bkmonitor_client() -> BKMonitorClient:
    """构建 BKMonitorClient 实例(添加授权信息)"""
    client = BKMonitorClient(stage=settings.APIGW_ENVIRONMENT, endpoint=settings.BK_API_URL_TMPL)
    client.update_bkapi_authorization(bk_app_code=settings.BK_APP_CODE, bk_app_secret=settings.BK_APP_SECRET)
    return client
