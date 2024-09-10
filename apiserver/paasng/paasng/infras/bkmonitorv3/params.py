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

from datetime import datetime
from typing import Dict, List, Optional, Union

from attrs import define

from paasng.infras.bkmonitorv3.exceptions import BkMonitorSpaceDoesNotExist
from paasng.infras.bkmonitorv3.models import BKMonitorSpace


def get_bk_biz_id(app_code: str) -> str:
    try:
        return BKMonitorSpace.objects.get(application__code=app_code).iam_resource_id
    except BKMonitorSpace.DoesNotExist as e:
        raise BkMonitorSpaceDoesNotExist(e)


def get_bk_biz_ids(app_codes: List[str]) -> List[str]:
    monitor_spaces = BKMonitorSpace.objects.filter(application__code__in=app_codes)
    if not monitor_spaces:
        raise BkMonitorSpaceDoesNotExist(BKMonitorSpace.DoesNotExist)
    return [space.iam_resource_id for space in monitor_spaces]


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

    app_code: List[str]
    start_time: datetime
    end_time: datetime
    environment: Optional[str] = None
    alert_code: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None

    def to_dict(self) -> Dict:
        """组装成 search_alerts 接口需要的参数"""
        d = {
            "start_time": int(self.start_time.timestamp()),
            "end_time": int(self.end_time.timestamp()),
            "bk_biz_ids": [int(biz_id) for biz_id in get_bk_biz_ids(self.app_code)],
            "page": 1,
            "page_size": 500,
            # 按照 ID 降序
            "ordering": ["-id"],
        }

        if self.status:
            d["status"] = [self.status]

        if query_string := self._build_query_string():
            d["query_string"] = query_string

        return d

    def _build_query_string(self) -> Optional[str]:
        """构建 query_string 参数. 查询语法参考
        https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html
        """
        # labels 设置在具体的 alert_rules/ascode/rules_tpl 模板中
        query_string = None
        query_labels = self._build_valid_args(self.environment, self.alert_code)
        if query_labels:
            query_string = f"labels:({query_labels})"

        if self.keyword:
            query_keyword = f"alert_name:({self.keyword} OR *{self.keyword}*)"
            query_string = self._build_valid_args(query_string, query_keyword)
        return query_string

    def _build_valid_args(self, *args) -> Optional[str]:
        """将非空参数拼接为 "arg1 AND arg2 AND arg3" 的形式"""
        valid_args: List[str] = list(filter(None, args))
        if not valid_args:
            return None
        return " AND ".join(valid_args)


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
            "bk_biz_id": get_bk_biz_id(self.app_code),
            "page": 1,
            "page_size": 500,
            "conditions": self._build_conditions(),
        }

    def _build_conditions(self) -> List:
        """构建 conditions 参数. 具体参数参考 search_alarm_strategy_without_biz 接口文档"""
        conditions: List[Dict[str, Union[str, List[str]]]] = []
        if self.status:
            conditions.append({"key": "strategy_status", "value": self.status})

        if self.keyword:
            conditions.append({"key": "strategy_name", "value": self.keyword})

        # labels 设置在具体的 alert_rules/ascode/rules_tpl 模板中
        query_labels = []
        if self.environment:
            query_labels.append(self.environment)

        if self.alert_code:
            query_labels.append(self.alert_code)

        conditions.append({"key": "label_name", "value": query_labels})
        return conditions
