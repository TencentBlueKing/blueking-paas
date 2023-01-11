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
from typing import Dict, Generator, List, Optional

from attrs import Factory, define

from paas_wl.monitoring.bkmonitor.client import make_bk_monitor_client
from paas_wl.monitoring.bkmonitor.exceptions import BkMonitorGatewayServiceError
from paas_wl.monitoring.metrics.clients.base import MetricQuery, MetricSeriesResult
from paas_wl.monitoring.metrics.constants import BKMONITOR_PROMQL_TMPL, MetricsResourceType, MetricsSeriesType
from paas_wl.monitoring.metrics.exceptions import RequestMetricBackendError

logger = logging.getLogger(__name__)


class BkMonitorMetricClient:
    query_tmpl_config = BKMONITOR_PROMQL_TMPL

    def general_query(
        self, queries: List[MetricQuery], container_name: str
    ) -> Generator[MetricSeriesResult, None, None]:
        """查询指定的各个指标数据"""
        for query in queries:
            try:
                if not query.is_ranged or not query.time_range:
                    raise ValueError('query metric in bkmonitor without time range is unsupported!')

                results = self._query_range(query.query, container_name=container_name, **query.time_range.to_dict())
            except Exception as e:
                logger.exception("fetch metrics failed, query: %s , reason: %s", query.query, e)
                # 某些 metrics 如果失败，不影响其他数据
                results = []

            yield MetricSeriesResult(type_name=query.type_name, results=results)

    def get_query_template(self, resource_type: MetricsResourceType, series_type: MetricsSeriesType) -> str:
        return self.query_tmpl_config[resource_type][series_type]

    def _query_range(self, promql, start, end, step, container_name: str = "") -> List:
        """范围请求API

        :param promql: 具体请求QL
        :param start: 开始时间
        :param end: 结束时间
        :param step: 步长
        :param container_name: 请求容器名
        """
        logger.info('prometheus query_range promql: %s, start: %s, end: %s, step: %s', promql, start, end, step)
        try:
            series = self._request(promql, start, end, step)
            ret = BkPromResult.from_series(series).get_raw_by_container_name(container_name)
            if ret:
                return ret.get("values", [])
        except Exception as e:
            logger.warning("failed to get metric results: %s", e)

        return []

    @staticmethod
    def _request(promql: str, start: str, end: str, step: str) -> List:
        """请求蓝鲸监控时序数据 API，若成功则返回 Series 数据(list)，否则抛出异常"""

        try:
            client = make_bk_monitor_client()
            series = client.promql_query(promql, start, end, step)
        except BkMonitorGatewayServiceError as e:
            logger.warning("fetch metrics failed, promql: %s, start: %s, end: %s, step: %s", promql, start, end, step)
            raise RequestMetricBackendError(str(e))

        return series


@define
class BkPromRangeSingleMetric:
    """蓝鲸监控 PromQL 查询指标数据"""

    class MetricResult:
        container_name: str

        def __init__(self, *args, **kwargs):
            _name = kwargs.get('container_name') or kwargs.get('container')
            self.container_name = str(_name)

        def to_raw(self):
            return dict(container_name=self.container_name)

    @define
    class ValuePair:
        timestamp: int
        value: str

        def __attrs_post_init__(self):
            # 时间戳转换为秒
            self.timestamp = int(self.timestamp / 1000)
            # 强制转换成 str 类型
            self.value = str(self.value)

        def to_raw(self):
            return [self.timestamp, self.value]

    metric: MetricResult
    values: List[ValuePair] = Factory(list)

    @property
    def container_name(self) -> str:
        return self.metric.container_name

    @classmethod
    def from_raw(cls, raw):
        return cls(
            metric=cls.MetricResult(**dict(zip(raw['group_keys'], raw['group_values']))),
            values=[cls.ValuePair(timestamp=timestamp, value=val) for (timestamp, val) in raw['values']],
        )

    def to_raw(self) -> dict:
        # 当前为了兼容原来的处理方法，会重新转换成 dict
        return {'metric': self.metric.to_raw(), 'values': [i.to_raw() for i in self.values] if self.values else []}


@define
class BkPromResult:
    """蓝鲸监控 PromQL 查询时序数据结果解析器"""

    results: List[BkPromRangeSingleMetric]

    @classmethod
    def from_series(cls, series: List[Dict]) -> 'BkPromResult':
        """直接根据蓝鲸监控返回的 series 数据，生成 BkPromResult"""
        if not series:
            raise ValueError("source series is empty")

        return cls(results=[BkPromRangeSingleMetric.from_raw(s) for s in series])

    def get_raw_by_container_name(self, container_name: str = "") -> Optional[Dict]:
        """通过 container name 获取结果"""
        # 保持原有兼容逻辑
        if not container_name:
            return self.results[0].to_raw()

        for i in self.results:
            if i.container_name == container_name:
                return i.to_raw()

        return None
