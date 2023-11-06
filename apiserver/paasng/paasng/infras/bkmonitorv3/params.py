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
from datetime import datetime
from typing import Dict, List, Optional, Union

from attrs import define

from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.platform.applications.models import Application


def get_bk_biz_id(app_code: str) -> str:
    app = Application.objects.get(code=app_code)
    monitor_space, _ = get_or_create_bk_monitor_space(app)
    return monitor_space.iam_resource_id


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

    def to_dict(self) -> Dict:
        """组装成 search_alerts 接口需要的参数"""
        d = {
            'start_time': int(self.start_time.timestamp()),
            'end_time': int(self.end_time.timestamp()),
            'bk_biz_ids': [get_bk_biz_id(self.app_code)],
            'page_size': 1,
            'page': 500,
            # 按照 ID 降序
            'ordering': ['-id'],
        }

        if self.status:
            d['status'] = [self.status]

        d['query_string'] = self._build_query_string()

        return d

    def _build_query_string(self) -> str:
        """构建 query_string 参数. 查询语法参考
        https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
        """
        # labels 设置在具体的 alert_rules/ascode/rules_tpl 模板中
        query_labels = "PAAS_BUILTIN"
        if self.environment:
            query_labels = f"{query_labels} AND {self.environment}"

        if self.alert_code:
            query_labels = f"{query_labels} AND {self.alert_code}"

        query_string = f"labels:({query_labels})"
        if self.keyword:
            query_string = f'{query_string} AND alert_name:{self.keyword}'
        return query_string


@define(kw_only=True)
class QueryAlarmStrategiesParams:
    """
    查询告警的参数

    :param app_code: 应用 code
    :param environment: 应用部署环境. 可选
    :param alert_code: 支持的告警 code, 如 high_cpu_usage. 可选
    :param status: 告警状态 (ALERT: 表示告警中, INVALID: 表示已失效, OFF: 表示已关闭, ON: 表示已开启). 可选
    :param keyword: 告警名称包含的关键字. 可选
    """

    app_code: str
    environment: Optional[str] = None
    alert_code: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None

    def to_dict(self) -> Dict:
        """组装成 search_alarm_strategy_without_biz 接口需要的参数"""
        return {
            'bk_biz_id': get_bk_biz_id(self.app_code),
            'page': 1,
            'page_size': 500,
            'conditions': self._build_conditions(),
        }

    def _build_conditions(self) -> List:
        """构建 conditions 参数. 具体参数参考 search_alarm_strategy_without_biz 接口文档"""
        conditions: List[Dict[str, Union[str, List[str]]]] = []
        if self.status:
            conditions.append({"key": "strategy_status", "value": self.status})

        if self.keyword:
            conditions.append({"key": "alert_name", "value": self.keyword})

        # labels 设置在具体的 alert_rules/ascode/rules_tpl 模板中
        query_labels = ["PAAS_BUILTIN"]
        if self.environment:
            query_labels.append(self.environment)

        if self.alert_code:
            query_labels.append(self.alert_code)

        conditions.append({"key": "label_name", "value": query_labels})
        return conditions
