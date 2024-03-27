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
from typing import Callable, Dict, List, Optional

from kubernetes.utils import parse_quantity

from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.processes.shim import ProcessManager
from paasng.misc.monitoring.metrics.constants import MetricsSeriesType
from paasng.misc.monitoring.metrics.models import MetricsInstanceResult, get_resource_metric_manager
from paasng.misc.monitoring.metrics.utils import MetricSmartTimeRange
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName, MetricsType
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


@dataclass
class ResSummary:
    """单类资源使用数据
    单位：
    - CPU 类型资源：m
    - 内存 类型资源：Mi
    """

    # 起始时间
    start: int = 0
    # 结束时间
    end: int = 0
    # 总计采样点数量
    cnt: int = 0
    # 资源使用中位数
    med: float = 0
    # 资源使用平均值
    avg: float = 0
    # 资源使用 p75
    p75: float = 0
    # 资源使用 p90
    p90: float = 0
    # 最大资源使用量
    max: float = 0


@dataclass
class ResRequirement:
    """资源集合"""

    # CPU 单位为 m
    cpu: int
    # 内存单位为 Mi
    memory: int


@dataclass
class ResQuota:
    """资源配额方案"""

    limits: ResRequirement
    requests: ResRequirement


@dataclass
class ProcSummary:
    """进程资源使用数据"""

    name: str
    replicas: int = 0
    quota: Optional[ResQuota] = None
    cpu: Optional[ResSummary] = None
    memory: Optional[ResSummary] = None
    current_plan: Optional[str] = None


@dataclass
class ModuleSummary:
    """模块资源使用数据"""

    module_name: str
    stag_procs: List[ProcSummary]
    prod_procs: List[ProcSummary]


@dataclass
class AppSummary:
    """应用资源使用数据"""

    app_code: str
    app_type: str
    modules: List[ModuleSummary]


class AppResQuotaCollector:
    """应用资源历史使用数据采集器"""

    def __init__(self, app: Application, step: str = "15m", time_range_str: str = "7d"):
        self.app = app
        self.query_metrics = [MetricsType.CPU.value, MetricsType.MEM.value]
        # 查询历史 7 天的数据，数据采样间隔为 15m，需要注意的是：如果中间发布过，则数据长度可能不足
        self.time_range = MetricSmartTimeRange(step=step, time_range_str=time_range_str)
        # 初始化云原生应用 资源配额方案 -> request 映射表
        self.bkapp_plan_to_request_map = {
            plan: (self._format_cpu(quota.cpu), self._format_memory(quota.memory))
            for plan, quota in PLAN_TO_REQUEST_QUOTA_MAP.items()
        }

    def collect(self) -> AppSummary:
        module_summaries = [self._calc_module_summary(module) for module in self.app.modules.all()]
        return AppSummary(app_code=self.app.code, app_type=self.app.type, modules=module_summaries)

    def _calc_module_summary(self, module: Module) -> ModuleSummary:
        stag_env = module.get_envs(AppEnvName.STAG)
        prod_env = module.get_envs(AppEnvName.PROD)
        return ModuleSummary(
            module_name=module.name,
            stag_procs=self._calc_proc_summaries(stag_env),
            prod_procs=self._calc_proc_summaries(prod_env),
        )

    def _calc_proc_summaries(self, env: ModuleEnvironment) -> List[ProcSummary]:
        proc_summaries = []
        try:
            for proc in ProcessManager(env).list_processes_specs():
                mgr = get_resource_metric_manager(env.engine_app.to_wl_obj(), proc["name"])
                result = mgr.get_all_instances_metrics(
                    resource_types=self.query_metrics,
                    time_range=self.time_range,
                    series_type=MetricsSeriesType.CURRENT,
                )
                proc_summaries.append(self._calc_proc_summary(proc, result))
        except Exception as e:
            logger.warning(f"failed to get env {env} process metrics: {e}")

        return proc_summaries

    def _calc_proc_summary(self, proc_spec: Dict, results: List[MetricsInstanceResult]) -> ProcSummary:
        cpu_metrics, mem_metrics = [], []

        replicas = 0
        for mir in results:
            for mrr in mir.results:
                if mrr.type_name == MetricsType.CPU.value:
                    for msr in mrr.results:
                        cpu_metrics.extend(msr.results)
                        # 仅统计 CPU 类型即可，内存指标数量应该是一致的
                        replicas += 1
                elif mrr.type_name == MetricsType.MEM.value:
                    for msr in mrr.results:
                        mem_metrics.extend(msr.results)

        if not (cpu_metrics and mem_metrics):
            return ProcSummary(name=proc_spec["name"])

        cpu_summary = self._calc_res_summary(cpu_metrics, trans_unit_func=lambda x: x * 1000)
        mem_summary = self._calc_res_summary(mem_metrics, trans_unit_func=lambda x: x / 1024 / 1024)
        res_quota = self._get_proc_res_quota(proc_spec)
        return ProcSummary(
            name=proc_spec["name"],
            replicas=replicas,
            quota=res_quota,
            cpu=cpu_summary,
            memory=mem_summary,
            current_plan=proc_spec["plan_name"],
        )

    def _calc_res_summary(self, metrics: List, trans_unit_func: Callable) -> ResSummary:
        summary = ResSummary()
        # 时间戳本身就是升序的
        summary.start = metrics[0][0]
        summary.end = metrics[-1][0]
        # 只保留指标值，并重新排序
        metrics = sorted(
            [
                # 转换单位，保留两位小数
                round(trans_unit_func(float(metric)), 2)
                for _, metric in metrics
                if (metric and metric != "None")
            ]
        )
        # 可能出现过滤后为空的情况
        if not metrics:
            return summary

        # 采样点数量
        summary.cnt = len(metrics)
        # 中位数
        half = len(metrics) // 2
        summary.med = round((metrics[half] + metrics[~half]) / 2, 2)
        # 平均值
        summary.avg = round(sum(metrics) / len(metrics), 2)
        # p75（注：不是标准 p75，但可以作为参考）
        summary.p75 = metrics[int(len(metrics) / 4 * 3)]
        # p90（注：不是标准 p90，但可以作为参考）
        summary.p90 = metrics[int(len(metrics) / 10 * 9)]
        # 最大值
        summary.max = metrics[-1]
        return summary

    def _get_proc_res_quota(self, proc_spec: Dict) -> ResQuota:
        """获取应用的资源套餐方案"""
        res_limits = proc_spec.get("resource_limit", {})
        res_requests = proc_spec.get("resource_requests", {})
        return ResQuota(
            limits=ResRequirement(
                cpu=self._format_cpu(res_limits["cpu"]),
                memory=self._format_memory(res_limits["memory"]),
            ),
            requests=ResRequirement(
                cpu=self._format_cpu(res_requests["cpu"]),
                memory=self._format_memory(res_requests["memory"]),
            ),
        )

    @staticmethod
    def _format_cpu(cpu: str) -> int:
        """将 CPU 资源配额转换为以 m 为单位的值"""
        return int(parse_quantity(cpu) * 1000)

    @staticmethod
    def _format_memory(memory: str) -> int:
        """将内存资源配额转换为以 Mi 为单位的值"""
        return int(parse_quantity(memory) / (1024 * 1024))
