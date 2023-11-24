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
from dataclasses import dataclass, field
from typing import Generator, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth
from requests.status_codes import codes

from paas_wl.bk_app.monitoring.metrics.clients.base import MetricQuery, MetricSeriesResult
from paas_wl.bk_app.monitoring.metrics.constants import RAW_PROMQL_TMPL, MetricsResourceType, MetricsSeriesType
from paas_wl.bk_app.monitoring.metrics.exceptions import RequestMetricBackendError

logger = logging.getLogger(__name__)


class PrometheusMetricClient:
    query_tmpl_config = RAW_PROMQL_TMPL

    def __init__(self, basic_auth: Tuple[str, str], host: str):
        self.basic_auth = basic_auth
        self.host = host

    def general_query(
        self, queries: List["MetricQuery"], container_name: str
    ) -> Generator["MetricSeriesResult", None, None]:
        """查询指定的各个指标数据"""
        for query in queries:
            try:
                if not query.is_ranged or not query.time_range:
                    raise ValueError("for security reasons, query metric without time range isn't allowed!")

                results = self._query_range(query.query, container_name=container_name, **query.time_range.to_dict())
            except Exception as e:
                logger.exception("fetch metrics failed, query: %s, reason: %s", query.query, e)
                # 某些 metrics 如果失败，不影响其他数据
                results = []

            yield MetricSeriesResult(type_name=query.type_name, results=results)

    def get_query_promql(
        self, resource_type: MetricsResourceType, series_type: MetricsSeriesType, instance_name: str, cluster_id: str
    ) -> str:
        tmpl = self.query_tmpl_config[resource_type][series_type]
        return tmpl.format(instance_name=instance_name, cluster_id=cluster_id)

    def _query_range(self, query, start, end, step, container_name: str = "") -> List:
        """范围请求API

        :param query: 具体请求的 PromQL
        :param start: 开始时间
        :param end: 结束时间
        :param step: 步长
        :param container_name: 容器名称
        """
        path = "api/v1/query_range"
        params = {"query": query, "start": start, "end": end, "step": step}
        logger.info("prometheus query_range: %s", params)
        result = self._request(method="GET", path=path, params=params, timeout=30)
        try:
            ret = PromResult.from_resp(result).get_raw_by_container_name(container_name)
            if ret:
                return ret.get("values", [])
            else:
                return []
        except ValueError as e:
            logger.warning("failed to get metric results, for %s", e)
            return []
        except Exception:
            logger.exception("failed to get metrics results")
            return []

    def _request(self, method, path, desired_code=codes.ok, **kwargs):
        """Wrap request.request to provide a universal requests for prometheus
        return value has been formatted as json
        """
        url = f"{self.host}/{path}"
        logger.debug(f"Prometheus client sending request to [{method}]{url}, kwargs={kwargs}.")

        if self.basic_auth:
            kwargs["auth"] = HTTPBasicAuth(*self.basic_auth)

        # long time range may cause timeout
        resp = requests.request(method, url, **kwargs)

        if not resp.status_code == desired_code:
            logger.warning("fetch<%s> metrics failed", url)
            raise RequestMetricBackendError(resp)

        result = resp.json()
        if not result.get("status"):
            logger.warning("fetch<%s> metrics failed", url)
            raise RequestMetricBackendError(resp)

        return result


@dataclass
class PromRangeSingleMetric:
    class MetricResult:
        container_name: str

        def __init__(self, *args, **kwargs):
            _name = kwargs.get("container_name") or kwargs.get("container")
            self.container_name = str(_name)

        def to_raw(self):
            return dict(container_name=self.container_name)

    @dataclass
    class ValuePair:
        timestamp: int
        value: str

        def to_raw(self):
            return [self.timestamp, self.value]

    metric: MetricResult
    values: List[ValuePair] = field(default_factory=list)

    @property
    def container_name(self) -> str:
        return self.metric.container_name

    @classmethod
    def from_raw(cls, raw):
        return cls(
            metric=cls.MetricResult(**raw["metric"]),
            values=[cls.ValuePair(timestamp=i[0], value=i[1]) for i in raw["values"]],
        )

    def to_raw(self) -> dict:
        # 当前为了兼容原来的处理方法，会重新转换成 dict
        return dict(metric=self.metric.to_raw(), values=[i.to_raw() for i in self.values] if self.values else [])


@dataclass
class PromResult:
    """原生 Prometheus 结果解析器"""

    results: List[PromRangeSingleMetric]

    @classmethod
    def from_resp(cls, raw_resp: dict) -> "PromResult":
        if not raw_resp:
            raise ValueError("No valid results")

        if not raw_resp.get("data", {}).get("result", []):
            if raw_resp.get("warnings"):
                raise ValueError(raw_resp.get("warnings"))
            else:
                raise ValueError("empty results")

        return cls(results=[PromRangeSingleMetric.from_raw(r) for r in raw_resp.get("data", {}).get("result", [])])

    def get_raw_by_container_name(self, container_name: str = "") -> Optional[dict]:
        """通过 container name 获取结果"""
        # 保持原来的兼容逻辑
        if not container_name:
            return self.results[0].to_raw()

        for i in self.results:
            if i.container_name == container_name:
                return i.to_raw()

        return None
