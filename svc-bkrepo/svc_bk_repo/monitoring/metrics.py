# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import datetime

from prometheus_client.core import CollectorRegistry, GaugeMetricFamily

global_registry = CollectorRegistry()


class BKRepoMetricsCollector:
    def collect(self):
        from svc_bk_repo.monitoring.models import RepoQuotaStatistics

        dt = datetime.datetime.now()
        timestamp = dt.timestamp()
        quota_used_rate_metric = GaugeMetricFamily(
            "bkrepo_quota_used_rate_metrics", "bkrepo Quota Used Rate Metrics", labels=["service_id", "instance_id", "repo_name"]
        )
        for repo_quota_stat in RepoQuotaStatistics.objects.all():
            quota_used_rate_metric.add_metric(
                [
                    str(repo_quota_stat.instance.service_id),
                    str(repo_quota_stat.instance_id),
                    str(repo_quota_stat.repo_name)
                 ],
                repo_quota_stat.quota_used_rate,
                timestamp=timestamp,
            )

        yield quota_used_rate_metric


global_registry.register(BKRepoMetricsCollector())
