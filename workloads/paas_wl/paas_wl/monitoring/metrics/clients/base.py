# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Generator, List, Optional, Protocol, Union

from paas_wl.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paas_wl.monitoring.metrics.utils import MetricSmartTimeRange


class MetricClient(Protocol):
    def general_query(
        self, queries: List['MetricQuery'], container_name: str
    ) -> Generator['MetricSeriesResult', None, None]:
        raise NotImplementedError

    def get_query_template(self, resource_type: MetricsResourceType, series_type: MetricsSeriesType) -> str:
        """subclass may raise keyError if not given query_tmpl_config"""
        raise NotImplementedError


@dataclass
class MetricQuery:
    """Metric Query
    封装 query 提供更快捷的查询
    """

    type_name: Union[MetricsSeriesType, str]
    query: str
    time_range: Optional[MetricSmartTimeRange] = None

    @property
    def is_ranged(self):
        return bool(self.time_range)


@dataclass
class MetricSeriesResult:
    """metrics series result"""

    type_name: Union[MetricsSeriesType, str]
    # 暂时使用 List 不做更多解析
    results: List

    def __len__(self):
        return len(self.results)
