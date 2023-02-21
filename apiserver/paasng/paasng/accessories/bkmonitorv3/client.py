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
from typing import Dict, List

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from typing_extensions import Protocol

from paasng.accessories.bkmonitorv3.backend.apigw import Client
from paasng.accessories.bkmonitorv3.backend.esb import get_client_by_username
from paasng.accessories.bkmonitorv3.exceptions import (
    BkMonitorApiError,
    BkMonitorGatewayServiceError,
    BkMonitorSpaceDoesNotExist,
)
from paasng.accessories.bkmonitorv3.params import QueryAlertsParams

logger = logging.getLogger(__name__)


class BkMonitorBackend(Protocol):
    """Describes protocols of calling API service"""

    def metadata_get_space_detail(self, *args, **kwargs) -> Dict:
        ...

    def metadata_create_space(self, *args, **kwargs) -> Dict:
        ...

    def metadata_update_space(self, *args, **kwargs) -> Dict:
        ...

    def search_alert(self, *args, **kwargs) -> Dict:
        ...


class BkMonitorClient:
    """API provided by BK Monitor

    :param backend: client 后端实际的 backend
    :param space_type_id: 空间类型ID， 默认值为 bksaas, 表示蓝鲸应用
    """

    def __init__(self, backend: BkMonitorBackend, space_type_id: str = 'bksaas'):
        self.client = backend
        self.space_type_id = space_type_id

    def get_or_create_space(self, app_code: str, app_name: str, creator: str) -> str:
        try:
            space_uid = self._get_space_detail(app_code)
        except BkMonitorSpaceDoesNotExist:
            space_uid = self._create_space(app_code, app_name, creator)

        return space_uid

    def update_space(self, app_code: str, app_name: str, updater: str) -> str:
        """更新空间"""
        data = {
            "space_name": app_name,
            "space_id": app_code,
            "space_type_id": self.space_type_id,
            "updater": updater,
        }
        try:
            resp = self.client.metadata_update_space(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to update app space on BK Monitor') from e

        if not resp.get('result'):
            logger.exception(f'Failed to update app space on BK Monitor, resp:{resp} \ndata: {data}')
            raise BkMonitorApiError(resp['message'])

        return resp.get('data', {}).get('space_uid')

    def query_alerts(self, query_params: QueryAlertsParams) -> List:
        """查询告警

        :param query_params: 查询告警的条件参数
        """
        try:
            resp = self.client.search_alert(json=query_params.to_dict())
        except APIGatewayResponseError:
            # 详细错误信息 bkapi_client_core 会自动记录
            raise BkMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if not resp.get('result'):
            raise BkMonitorApiError(resp['message'])

        return resp.get('data', {}).get('alerts', [])

    def _get_space_detail(self, app_code: str) -> str:
        """获取空间详情"""
        data = {"space_type_id": self.space_type_id, "space_id": app_code}
        try:
            resp = self.client.metadata_get_space_detail(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to get app space detail on BK Monitor') from e

        # 目前监控的API返回值只有 true 和 false，没有更详细的错误码来确定是否空间已经存在
        # 监控侧暂时也没有规划添加错误码来标识空间是否已经存在
        if not resp.get('result'):
            logger.exception(f'Failed to get app({app_code}) space detail on BK Monitor, resp:{resp}')
            raise BkMonitorSpaceDoesNotExist(resp['message'])

        return resp.get('data', {}).get('space_uid')

    def _create_space(self, app_code: str, app_name: str, creator: str) -> str:
        """在蓝鲸监控上创建应用对应的空间"""
        data = {
            "space_name": app_name,
            "space_id": app_code,
            "space_type_id": self.space_type_id,
            "creator": creator,
        }
        try:
            resp = self.client.metadata_create_space(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to create app space on BK Monitor') from e

        if not resp.get('result'):
            logger.error(f'Failed to create app space on BK Monitor, resp:{resp} \ndata: {data}')
            raise BkMonitorApiError(resp['message'])

        return resp.get('data', {}).get('space_uid')


def make_bk_monitor_client() -> BkMonitorClient:
    if settings.ENABLE_BK_MONITOR_APIGW:
        apigw_client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_MONITOR_APIGW_SERVICE_STAGE)
        apigw_client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
    return BkMonitorClient(apigw_client.api)

    # ESB 开启了免用户认证，但是又限制了用户名不能为空，所以需要给一个随机字符串
    esb_client = get_client_by_username("admin")
    return BkMonitorClient(esb_client.monitor_v3)
