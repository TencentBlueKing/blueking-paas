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
from typing import List

from paas_wl.bk_app.monitoring.metrics.exceptions import RequestMetricBackendError
from paas_wl.bk_app.monitoring.metrics.models import get_resource_metric_manager
from paas_wl.bk_app.monitoring.metrics.utils import MetricSmartTimeRange
from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)


def list_app_proc_metrics(
    wl_app: WlApp,
    process_type: str,
    instance_name: str,
    query_metrics: List[str],
    time_range: MetricSmartTimeRange,
):
    mgr = get_resource_metric_manager(wl_app, process_type)
    try:
        # 请求某个特定 instance 的 metrics
        instance_result = mgr.get_instance_metrics(
            time_range=time_range,
            instance_name=instance_name,
            resource_types=query_metrics,
        )
    except Exception as e:
        raise RequestMetricBackendError(f"failed to request Metric backend: {e}")

    return instance_result


def list_app_proc_all_metrics(
    wl_app: WlApp,
    process_type: str,
    query_metrics: List[str],
    time_range: MetricSmartTimeRange,
):
    mgr = get_resource_metric_manager(wl_app, process_type)
    try:
        # 请求所有 instance 的 metrics
        instance_result = mgr.get_all_instances_metrics(time_range=time_range, resource_types=query_metrics)
    except Exception as e:
        raise RequestMetricBackendError(f"failed to request Metric backend: {e}")

    return instance_result
