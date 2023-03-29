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
"""Utils for monitoring engine related stuff
"""
import datetime
import logging
from typing import Optional

import arrow
from prometheus_client.core import GaugeMetricFamily

from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.metrics.collector import cb_metric_collector
from paasng.platform.core.storages.cache import region as cache_region

from .constants import JobStatus
from .models.deployment import Deployment

logger = logging.getLogger(__name__)


def count_frozen_deployments(edge_seconds: int = 90, now: Optional[datetime.datetime] = None) -> int:
    """Count frozen deployments

    :param edge_seconds: if a pending deployment's has no updates in `edge_seconds`, it will be counted as "frozen"
    :param now: current datetime, default to `datetime.datetime.now`
    """
    edge_date = arrow.get(now).shift(seconds=-edge_seconds)

    logger.info('Start counting frozen deployments since {}'.format(edge_date.format()))
    # Set `created__lte` to narrow source dataset, while it's not required because deployment_is_frozen will filter
    # unqualified deployments anyway.
    deploys = Deployment.objects.filter(status=JobStatus.PENDING.value, created__lte=edge_date.datetime)

    frozen_deployments_cnt = sum(deployment_is_frozen(deployment, edge_date.datetime) for deployment in deploys)
    logger.info('Frozen deployments count: {}'.format(frozen_deployments_cnt))
    return frozen_deployments_cnt


def deployment_is_frozen(deployment: Deployment, since: datetime.datetime) -> bool:
    """Check if a deployment is frozen since given moment"""
    # Ignore fresh deployments
    if deployment.created > since:
        return False

    # Deployment with no build process was frozen
    if not deployment.build_process_id:
        return True

    client = EngineDeployClient(deployment.get_engine_app())
    log_lines = client.list_build_proc_logs(deployment.build_process_id)

    # Deployment with no logs lines was frozen
    if not log_lines:
        return True

    # Deployment which has no new lines in `edge_seconds` was frozen
    last_log_line = log_lines[-1]
    try:
        last_line_created = arrow.get(last_log_line['created'])
    except KeyError:
        # Backward compatibility
        return False
    return last_line_created < arrow.get(since)


class FrozenDeploymentsMetric:
    name = 'frozen_deployments'
    description = 'count of frozen deployments'

    @classmethod
    def calc_metric(cls) -> GaugeMetricFamily:
        """获取 metric"""
        cached_count_frozen_deployments = cache_region.cache_on_arguments(namespace='v1', expiration_time=60)(
            count_frozen_deployments
        )
        value = cached_count_frozen_deployments()
        return GaugeMetricFamily(cls.name, cls.description, value)

    @classmethod
    def describe_metric(cls) -> GaugeMetricFamily:
        """描述 metric"""
        return GaugeMetricFamily(cls.name, cls.description)


def register_metrics():
    """Register metrics for engine app"""
    cb_metric_collector.add(FrozenDeploymentsMetric)
