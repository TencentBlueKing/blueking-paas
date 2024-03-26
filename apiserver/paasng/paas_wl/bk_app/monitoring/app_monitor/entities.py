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
from typing import Dict, List, Optional

from . import constants


@dataclass
class Endpoint:
    # 蓝鲸监控采集 metrics 的间隔
    interval: str = constants.METRICS_INTERVAL
    # SaaS 暴露 metrics 的路径, 根据约定只能是 /metrics
    path: str = constants.METRICS_PATH
    # SaaS 暴露 metrics 的端口名, 根据约定只能是 metrics
    port: str = constants.METRICS_PORT_NAME
    # Metric 重标签配置, 由集群运维负责控制下发
    metric_relabelings: Optional[List[Dict]] = None


@dataclass
class ServiceSelector:
    # matchLabels 用于过滤蓝鲸监控 ServiceMonitor 监听的 Service
    matchLabels: Dict[str, str]
