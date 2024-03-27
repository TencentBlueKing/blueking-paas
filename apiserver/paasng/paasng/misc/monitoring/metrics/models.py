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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generator, List, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.readers import instance_kmodel, process_kmodel
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.misc.monitoring.metrics.clients import (
    BkMonitorMetricClient,
    MetricClient,
    MetricQuery,
    MetricSeriesResult,
    PrometheusMetricClient,
)
from paasng.misc.monitoring.metrics.constants import MetricsResourceType, MetricsSeriesType
from paasng.misc.monitoring.metrics.exceptions import AppInstancesNotFoundError, AppMetricNotSupportedError
from paasng.misc.monitoring.metrics.utils import MetricSmartTimeRange

if TYPE_CHECKING:
    from paas_wl.bk_app.processes.kres_entities import Process

logger = logging.getLogger(__name__)


@dataclass
class MetricsResourceResult:
    type_name: MetricsResourceType
    results: List[MetricSeriesResult]


@dataclass
class MetricsInstanceResult:
    instance_name: str
    results: List[MetricsResourceResult]

    def __len__(self):
        return len(self.results)


class ResourceMetricManager:
    def __init__(self, process: "Process", metric_client: MetricClient, bcs_cluster_id: str):
        self.process = process
        self.metric_client = metric_client
        self.bcs_cluster_id = bcs_cluster_id
        if not self.process.instances:
            raise ValueError("Process should contain info of instances when querying metrics")

    def gen_all_series_query(
        self,
        resource_type: MetricsResourceType,
        instance_name: str,
        time_range: MetricSmartTimeRange,
    ) -> Generator[MetricQuery, None, None]:
        """get all series type queries"""

        # not expose request series
        for series_type in [MetricsSeriesType.CURRENT.value, MetricsSeriesType.LIMIT.value]:
            try:
                yield self.gen_series_query(series_type, resource_type, instance_name, time_range)  # type: ignore
            except KeyError:
                logger.info("%s type not exist in query tmpl", series_type)
                continue

    def gen_series_query(
        self,
        series_type: MetricsSeriesType,
        resource_type: MetricsResourceType,
        instance_name: str,
        time_range: MetricSmartTimeRange,
    ) -> MetricQuery:
        """get single metrics type query"""
        promql = self.metric_client.get_query_promql(resource_type, series_type, instance_name, self.bcs_cluster_id)
        return MetricQuery(type_name=series_type, query=promql, time_range=time_range)

    def get_instance_metrics(
        self,
        instance_name: str,
        resource_types: List[MetricsResourceType],
        time_range: MetricSmartTimeRange,
        series_type: Optional[MetricsSeriesType] = None,
    ) -> List[MetricsResourceResult]:
        """query metrics at Engine Application level"""

        resource_results = []
        for resource_type in resource_types:
            if series_type:
                queries = [
                    self.gen_series_query(
                        series_type=series_type,
                        resource_type=resource_type,
                        instance_name=instance_name,
                        time_range=time_range,
                    )
                ]
            else:
                queries = list(
                    self.gen_all_series_query(
                        resource_type=resource_type, instance_name=instance_name, time_range=time_range
                    )
                )

            results = list(self.metric_client.general_query(queries, self.process.main_container_name))
            resource_results.append(MetricsResourceResult(type_name=resource_type, results=results))

        return resource_results

    def get_all_instances_metrics(
        self,
        resource_types: List[MetricsResourceType],
        time_range: MetricSmartTimeRange,
        series_type: Optional[MetricsSeriesType] = None,
    ) -> List[MetricsInstanceResult]:
        all_instances_metrics = []
        for instance in self.process.instances:
            all_instances_metrics.append(
                MetricsInstanceResult(
                    instance_name=instance.name,
                    results=self.get_instance_metrics(
                        resource_types=resource_types,
                        instance_name=instance.name,
                        time_range=time_range,
                        series_type=series_type,
                    ),
                )
            )

        return all_instances_metrics


def get_resource_metric_manager(app: WlApp, process_type: str):
    try:
        cluster = get_cluster_by_app(app)
    except ObjectDoesNotExist:
        raise RuntimeError("no cluster can be found, query aborted")

    if not cluster.bcs_cluster_id:
        raise AppMetricNotSupportedError("cluster this process deployed isn't a bcs cluster, failed to get metrics")

    # 不同的指标数据来源依赖配置不同，需要分别检查
    if cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_MONITOR):
        if not settings.ENABLE_BK_MONITOR:
            raise AppMetricNotSupportedError("bkmonitor in this edition not enabled")
        if not cluster.bk_biz_id:
            raise AppMetricNotSupportedError("cluster this process deployed hasn't bkcc info, failed to get metrics")
        metric_client = BkMonitorMetricClient(bk_biz_id=cluster.bk_biz_id)

    else:
        if not settings.MONITOR_CONFIG:
            raise AppMetricNotSupportedError("MONITOR_CONFIG unset")
        metric_client = PrometheusMetricClient(**settings.MONITOR_CONFIG["metrics"]["prometheus"])  # type: ignore

    # 获取 WlApp 对应的进程实例
    try:
        process = process_kmodel.get_by_type(app, process_type)
        process.instances = instance_kmodel.list_by_process_type(app, process_type)
    except Exception:
        raise AppInstancesNotFoundError("failed to get process instances info")

    if not process.instances:
        raise AppInstancesNotFoundError("current process hasn't instances")

    return ResourceMetricManager(
        process=process,
        metric_client=metric_client,
        bcs_cluster_id=cluster.bcs_cluster_id,
    )
