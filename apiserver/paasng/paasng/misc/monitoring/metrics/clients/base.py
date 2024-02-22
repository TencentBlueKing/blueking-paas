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
from dataclasses import dataclass
from typing import Generator, List, Optional, Protocol, Union

from paasng.misc.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paasng.misc.monitoring.metrics.utils import MetricSmartTimeRange


class MetricClient(Protocol):
    def general_query(
        self, queries: List["MetricQuery"], container_name: str
    ) -> Generator["MetricSeriesResult", None, None]:
        raise NotImplementedError

    def get_query_promql(
        self, resource_type: MetricsResourceType, series_type: MetricsSeriesType, instance_name: str, cluster_id: str
    ) -> str:
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
