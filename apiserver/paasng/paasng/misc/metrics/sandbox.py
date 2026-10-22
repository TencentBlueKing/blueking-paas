# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""沙箱数量的拉取式指标"""

import logging

from django.db.models import Count
from prometheus_client.core import GaugeMetricFamily

from paasng.platform.agent_sandbox.e2b.constants import E2BSandboxStatus
from paasng.platform.agent_sandbox.models import E2BSandbox, Sandbox

logger = logging.getLogger(__name__)


class _SandboxCountMetricBase:
    """按 (应用, 集群, ...) 聚合沙箱数量的回调指标基类"""

    name: str
    description: str
    labels: tuple[str, ...]

    @classmethod
    def calc_metric(cls) -> GaugeMetricFamily:
        family = GaugeMetricFamily(cls.name, cls.description, labels=list(cls.labels))
        try:
            for labels, value in cls.iter_samples():
                family.add_metric(list(labels), value)
        except Exception:
            # 采集失败不能让整个 /metrics 变成 500, 降级为 "本次不产出该指标" 并留下日志
            logger.exception("failed to collect metric %s", cls.name)
            return GaugeMetricFamily(cls.name, cls.description, labels=list(cls.labels))
        return family

    @classmethod
    def describe_metric(cls) -> GaugeMetricFamily:
        return GaugeMetricFamily(cls.name, cls.description, labels=list(cls.labels))

    @classmethod
    def iter_samples(cls):
        """产出 (标签值元组, 数量), 顺序与 labels 一致"""
        raise NotImplementedError


class SandboxCountMetric(_SandboxCountMetricBase):
    """沙箱数量 (不包含 e2b). 未软删除的记录均计入, 包括 err_creating"""

    name = "agent_sandbox_count"
    description = "number of agent sandboxes"
    labels = ("app_code", "cluster", "workload_type", "status")

    @classmethod
    def iter_samples(cls):
        rows = (
            Sandbox.objects.filter(deleted_at__isnull=True)
            .values_list("application__code", "target", "workload_type", "status")
            .annotate(count=Count("uuid"))
        )
        for app_code, cluster, workload_type, status, count in rows:
            yield (app_code, cluster, workload_type, status), count


class E2BSandboxCountMetric(_SandboxCountMetricBase):
    """e2b 接口创建的沙箱数量, 只统计存活中的记录"""

    name = "agent_sandbox_e2b_count"
    description = "number of e2b sandboxes"
    labels = ("app_code", "cluster", "status")

    @classmethod
    def iter_samples(cls):
        rows = (
            E2BSandbox.objects.filter(status__in=E2BSandboxStatus.active_values())
            .values_list("application__code", "cluster_name", "status")
            .annotate(count=Count("uuid"))
        )
        for app_code, cluster, status, count in rows:
            yield (app_code, cluster, status), count
