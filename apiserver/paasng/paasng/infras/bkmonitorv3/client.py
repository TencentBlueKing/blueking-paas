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
from typing import Dict, List, Optional, Union

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from typing_extensions import Protocol

from paasng.infras.bkmonitorv3.backend.apigw import Client
from paasng.infras.bkmonitorv3.backend.esb import get_client_by_username
from paasng.infras.bkmonitorv3.definitions import BkMonitorSpace
from paasng.infras.bkmonitorv3.exceptions import (
    BkMonitorApiError,
    BkMonitorGatewayServiceError,
    BkMonitorSpaceDoesNotExist,
)
from paasng.infras.bkmonitorv3.params import QueryAlarmStrategiesParams, QueryAlertsParams

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

    def search_alarm_strategy_v3(self, *args, **kwargs) -> Dict:
        ...

    def promql_query(self, *args, **kwargs) -> Dict:
        ...

    def as_code_import_config(self, *args, **kwargs) -> Dict:
        ...


class BKMonitorSpaceManager:
    """BK Monitor Space Management API provider"""

    def __init__(self, backend: BkMonitorBackend):
        self.client = backend

    def create_space(self, space: BkMonitorSpace) -> BkMonitorSpace:
        """在蓝鲸监控上创建应用对应的空间"""
        data = {
            "space_name": space.space_name,
            "space_id": space.space_id,
            "space_type_id": space.space_type_id.value,
            "creator": space.creator,
        }
        try:
            resp = self.client.metadata_create_space(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to create space on BK Monitor') from e

        if not resp.get('result'):
            logger.error('Failed to create space on BK Monitor, resp:%s \ndata: %s', resp, data)
            raise BkMonitorApiError(resp['message'])

        resp_data = resp.get('data', {})
        return BkMonitorSpace(
            space_type_id=resp_data["space_type_id"],
            space_id=resp_data["space_id"],
            space_name=resp_data["space_name"],
            creator=resp_data["creator"],
            id=resp_data["id"],
            space_uid=resp_data["space_uid"],
            extra_info=resp_data,
        )

    def update_space(self, space: BkMonitorSpace) -> BkMonitorSpace:
        """更新空间"""
        data = {
            "space_name": space.space_name,
            "space_id": space.space_id,
            "space_type_id": space.space_type_id,
            "creator": space.creator,
        }
        try:
            resp = self.client.metadata_update_space(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to update app space on BK Monitor') from e

        if not resp.get('result'):
            logger.info(f'Failed to update app space on BK Monitor, resp:{resp} \ndata: {data}')
            raise BkMonitorApiError(resp['message'])

        resp_data = resp.get('data', {})
        return BkMonitorSpace(
            space_type_id=resp_data["space_type_id"],
            space_id=resp_data["space_id"],
            space_name=resp_data["space_name"],
            creator=resp_data["creator"],
            id=resp_data["id"],
            space_uid=resp_data["space_uid"],
            extra_info=resp_data,
        )

    def get_space_detail(self, space: BkMonitorSpace) -> BkMonitorSpace:
        """获取空间详情"""
        data = {"space_type_id": space.space_type_id, "space_id": space.space_id}
        try:
            resp = self.client.metadata_get_space_detail(data=data)
        except APIGatewayResponseError as e:
            raise BkMonitorGatewayServiceError('Failed to get app space detail on BK Monitor') from e

        # 目前监控的API返回值只有 true 和 false，没有更详细的错误码来确定是否空间已经存在
        # 监控侧暂时也没有规划添加错误码来标识空间是否已经存在
        if not resp.get('result'):
            logger.info('Failed to get space detail of %s on BK Monitor, resp: %s', space, resp)
            raise BkMonitorSpaceDoesNotExist(resp['message'])

        resp_data = resp.get('data', {})
        return BkMonitorSpace(
            space_type_id=resp_data["space_type_id"],
            space_id=resp_data["space_id"],
            space_name=resp_data["space_name"],
            creator=resp_data["creator"],
            id=resp_data["id"],
            space_uid=resp_data["space_uid"],
            extra_info=resp_data,
        )


class BkMonitorClient:
    """API provided by BK Monitor

    :param backend: client 后端实际的 backend
    """

    def __init__(self, backend: BkMonitorBackend):
        self.client = backend

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

    def query_alarm_strategies(self, query_params: QueryAlarmStrategiesParams) -> Dict:
        """查询告警策略

        :param query_params: 查询告警策略的条件参数
        """
        try:
            resp = self.client.search_alarm_strategy_v3(json=query_params.to_dict())
        except APIGatewayResponseError:
            # 详细错误信息 bkapi_client_core 会自动记录
            raise BkMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if not resp.get('result'):
            raise BkMonitorApiError(resp['message'])

        return resp.get('data', {})

    def promql_query(self, bk_biz_id: Optional[str], promql: str, start: str, end: str, step: str) -> List:
        """
        通过 promql 语法访问蓝鲸监控，获取容器 cpu / 内存等指标数据

        :param bk_biz_id: 集群绑定的蓝鲸业务 ID
        :param promql: promql 查询语句，可参考 PROMQL_TMPL
        :param start: 起始时间戳，如 "1622009400"
        :param end: 结束时间戳，如 "1622009500"
        :param step: 步长，如："1m"
        :returns: 时序数据 Series
        """
        params: Dict[str, Union[str, int, None]] = {
            'promql': promql,
            'start_time': start,
            'end_time': end,
            'step': step,
            'bk_biz_id': bk_biz_id,
        }

        # TODO: 监控功能对接蓝鲸应用空间时需要将参数修改成传递 space_uid
        headers = {'X-Bk-Scope-Space-Uid': f'bkcc__{bk_biz_id}'}
        try:
            resp = self.client.promql_query(headers=headers, data=params)
        except APIGatewayResponseError:
            # 详细错误信息 bkapi_client_core 会自动记录
            raise BkMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if resp.get('error'):
            raise BkMonitorApiError(resp['error'])

        return resp.get('data', {}).get('series', [])

    def as_code_import_config(
        self, configs: Dict, biz_or_space_id: int, config_group: str, overwrite: bool = False, incremental: bool = True
    ):
        """通过 ascode 下发告警规则

        :param biz_or_space_id: 业务或空间 ID
        :param config_group: 配置分组组名, 默认 default
        :param overwrite: 是否跨分组覆盖同名配置,
        :param incremental: 是否增量更新
        """
        try:
            resp = self.client.as_code_import_config(
                data={
                    "bk_biz_id": biz_or_space_id,
                    "configs": configs,
                    "app": config_group,
                    "overwrite": overwrite,
                    "incremental": incremental,
                }
            )
        except APIGatewayResponseError:
            raise BkMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if not resp.get('result'):
            raise BkMonitorApiError(resp['message'])


def _make_bk_minotor_backend() -> BkMonitorBackend:
    if settings.ENABLE_BK_MONITOR_APIGW:
        apigw_client = Client(
            endpoint=settings.BK_API_URL_TMPL,
            stage=settings.BK_MONITOR_APIGW_SERVICE_STAGE,
        )
        apigw_client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        return apigw_client.api

    # ESB 开启了免用户认证，但限制用户名不能为空，因此给默认用户名
    esb_client = get_client_by_username("admin")
    return esb_client.monitor_v3


def make_bk_monitor_client() -> BkMonitorClient:
    return BkMonitorClient(_make_bk_minotor_backend())


def make_bk_monitor_space_manager() -> BKMonitorSpaceManager:
    return BKMonitorSpaceManager(_make_bk_minotor_backend())
