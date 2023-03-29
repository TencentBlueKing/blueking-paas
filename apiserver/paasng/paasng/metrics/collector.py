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
from typing import Dict, Iterator, Type

from prometheus_client.core import Metric
from typing_extensions import Protocol

from paasng.metrics.basic_services.blob_store import BlobStoreAvailableMetric
from paasng.metrics.basic_services.mysql import MySQLAvailableMetric
from paasng.metrics.basic_services.redis import RedisAvailableMetric
from paasng.metrics.workloads.deployment import UnavailableDeploymentTotalMetric


class CallbackMetric(Protocol):
    """
    支持回调求值的 Metric

    :param name: 指标名
    :param description: 指标描述
    """

    name: str
    description: str

    @classmethod
    def calc_metric(cls) -> Metric:
        """获取 metric"""

    @classmethod
    def describe_metric(cls) -> Metric:
        """描述 metric"""


class CallbackMetricCollector:
    """采集器: 采集支持回调求值的 Metric"""

    def __init__(self):
        self._metrics: Dict[str, Type[CallbackMetric]] = {}

    def add(self, metric: Type[CallbackMetric]):
        self._metrics[metric.name] = metric

    def collect(self):
        for m in self._metrics.values():
            yield m.calc_metric()

    def describe(self) -> Iterator[Metric]:
        """describe the metrics that this collector provided"""
        for m in self._metrics.values():
            yield m.describe_metric()


cb_metric_collector = CallbackMetricCollector()

# 添加基础服务 metric 指标
cb_metric_collector.add(BlobStoreAvailableMetric)
cb_metric_collector.add(MySQLAvailableMetric)
cb_metric_collector.add(RedisAvailableMetric)
# 添加原 workloads metric 指标
cb_metric_collector.add(UnavailableDeploymentTotalMetric)
