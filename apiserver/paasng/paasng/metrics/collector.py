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
from typing import Callable, Dict, Generator, Tuple

from prometheus_client.core import GaugeMetricFamily


class CallbackGaugeCollector:
    """A custom metrics collection based on callback function"""

    def __init__(self):
        self._metrics: Dict[str, Tuple] = {}

    def add(self, name: str, description: str, callback: Callable):
        """Add a new gauge value

        :param callback: the function which returns latest gauge value
        """
        self._metrics[name] = (name, description, callback)

    def collect(self) -> Generator[GaugeMetricFamily, None, None]:
        for name, description, callback in self._metrics.values():
            metric = GaugeMetricFamily(name, description, callback())
            yield metric


cb_gauge_collector = CallbackGaugeCollector()
