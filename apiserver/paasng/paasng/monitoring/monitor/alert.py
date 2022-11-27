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
from datetime import datetime
from typing import Optional

from attr import define
from bkapi_client_core.exceptions import BKAPIError
from django.conf import settings

from .client import make_bkmonitor_client
from .exceptions import BKMonitorGatewayServiceError

logger = logging.getLogger(__name__)


@define(kw_only=True)
class QueryAlertsParams:
    """
    查询告警的参数

    :param app_code: 应用 code
    :param start_time: 发生时间. datetime 类型, 其对应的字符串格式 '%Y-%m-%d %H:%M:%S'
    :param end_time: 结束时间. datetime 类型, 其对应的字符串格式 '%Y-%m-%d %H:%M:%S'
    :param environment: 应用部署环境. 可选
    :param alert_code: 支持的告警 code, 如 high_cpu_usage. 可选
    :param status: 告警状态 (ABNORMAL: 表示未恢复, CLOSED: 已关闭, RECOVERED: 已恢复). 可选
    :param keyword: 告警名称包含的关键字. 可选
    """

    app_code: str
    start_time: datetime
    end_time: datetime
    environment: Optional[str] = None
    alert_code: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None

    def to_dict(self) -> dict:
        """组装成 search_alerts 接口需要的参数"""
        d = {
            'start_time': int(self.start_time.timestamp()),
            'end_time': int(self.end_time.timestamp()),
            'bk_biz_ids': [settings.MONITOR_AS_CODE_CONF.get('bk_biz_id')],
            # 按现有的查询, 只返回最多 5000 条可以满足需求
            'page_size': 5000,
            'page': 1,
            # 按照 ID 降序
            'ordering': ['-id'],
        }

        if self.status:
            d['status'] = self.status

        d['query_string'] = self._build_query_string()

        return d

    def _build_query_string(self) -> str:
        """构建 query_string 参数. 查询语法参考
        https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
        """
        alert_rule_name = f"{self.app_code}_*{self.environment or '*'}_{self.alert_code or '*'}"
        query_string = f"labels:(BKPAAS AND {self.app_code} AND {alert_rule_name})"
        if self.keyword:
            query_string = f'{query_string} AND alert_name:*{self.keyword}*'
        return query_string


class QueryAlerts:
    def __init__(self, params: QueryAlertsParams):
        self.params = params

    def query(self):
        try:
            resp = make_bkmonitor_client().api.search_alert(json=self.params.to_dict())
        except BKAPIError:
            # 详细错误信息 bkapi_client_core 会自动记录
            raise BKMonitorGatewayServiceError('an unexpected error when request bkmonitor apigw')

        if not resp.get('result'):
            raise BKMonitorGatewayServiceError(resp['message'])

        return resp.get('data', {}).get('alerts', [])
