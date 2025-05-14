# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Generator, List, Tuple

import arrow
from django.conf import settings
from django.utils import timezone

from paasng.infras.iam.helpers import fetch_application_members
from paasng.platform.evaluation.collectors.deployment import AppSummary as AppDeploySummary
from paasng.platform.evaluation.collectors.resource import AppSummary as AppResSummary
from paasng.platform.evaluation.collectors.resource import ProcSummary as ProcResSummary
from paasng.platform.evaluation.collectors.user_visit import AppSummary as AppVisitSummary
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport
from paasng.platform.evaluation.providers import StaffStatusProvider
from paasng.utils.basic import get_username_by_bkpaas_user_id


@dataclass
class EnvEvaluateResult:
    """环境运营情况评估结果"""

    issue_type: OperationIssueType = OperationIssueType.NONE
    issues: List[str] = field(default_factory=list)


@dataclass
class ModuleEvaluateResult:
    """模块运营情况评估结果"""

    envs: Dict[str, EnvEvaluateResult] = field(default_factory=dict)


@dataclass
class AppEvaluateResult:
    """应用运营情况评估结果"""

    issue_type: OperationIssueType = OperationIssueType.NONE
    issues: List[str] = field(default_factory=list)
    modules: Dict[str, ModuleEvaluateResult] = field(default_factory=dict)


class AppOperationEvaluator:
    """
    综合各项指标，评估应用运营情况

    注：评估结果有六种，优先级从高到低分别是：
      - ownerless 无主：指应用无人维护（管理员均处于离职状态）
      - undeploy 未部署：指应用未部署或已下线
      - idle 闲置：指应用没有访问量，且资源使用几乎没有波动
      - misconfigured 配置不当：指应用配置不当（申请过多资源但是使用率低于预期）
      - maintainless 缺少维护：指应用运行中，但是长期没有操作 / 部署
      - none 无（默认值）：指应用运营情况良好
    """

    def __init__(
        self,
        report: AppOperationReport,
        res_summary: AppResSummary,
        visit_summary: AppVisitSummary,
        deploy_summary: AppDeploySummary,
    ):
        self.report = report
        self.application = report.app

        self.res_summary = res_summary
        self.visit_summary = visit_summary
        self.deploy_summary = deploy_summary

        self.staff_status_provider = StaffStatusProvider()

        self.result = AppEvaluateResult(
            modules={
                mod.name: ModuleEvaluateResult(envs={env.environment: EnvEvaluateResult() for env in mod.envs.all()})
                for mod in self.application.modules.all()
            }
        )

    def evaluate(self) -> AppEvaluateResult:
        """评估应用运营情况"""
        for evaluate_func in [
            self._evaluate_by_operation_history,
            self._evaluate_by_resource_usage,
            self._evaluate_by_user_visit,
            self._evaluate_by_process_status,
            self._evaluate_by_app_members_status,
        ]:
            evaluate_func()

        return self.result

    def _evaluate_by_operation_history(self):
        # 应用纬度评估（部署 & 操作）
        # 注：没有部署记录的，算未部署，不算缺少维护
        if self.report.latest_deployed_at and self.report.latest_deployed_at < timezone.now() - timedelta(days=180):
            self.result.issues.append("应用最近半年没有部署记录")
            self.result.issue_type = OperationIssueType.MAINTAINLESS

        if not self.report.latest_operated_at:
            self.result.issues.append("应用没有操作记录")
            self.result.issue_type = OperationIssueType.MAINTAINLESS
        elif self.report.latest_operated_at < timezone.now() - timedelta(days=180):
            self.result.issues.append("应用最近半年没有操作记录")
            self.result.issue_type = OperationIssueType.MAINTAINLESS

        t_180_days_ago = timezone.now() - timedelta(days=180)
        # 环境纬度评估
        for mod_name, mod in self.deploy_summary.modules.items():
            for env_name, env in mod.envs.items():
                env_result = self.result.modules[mod_name].envs[env_name]
                # 注：没有部署记录的，算未部署，不算缺少维护
                if env.latest_deployed_at and arrow.get(env.latest_deployed_at).datetime < t_180_days_ago:
                    env_result.issues.append("该环境最近半年没有部署记录")
                    env_result.issue_type = OperationIssueType.MAINTAINLESS

    def _evaluate_by_resource_usage(self):
        """
        根据资源使用量评估应用

        TODO 后续可以进一步细化评估的指标
        """
        # 平均内存使用率不超过 15% 的，需要检查内存最大使用量，如果不及配额的 1/2，应该提示缩容
        if self.report.mem_usage_avg and self.report.mem_usage_avg < 0.15:
            for mod_name, env_name, proc in self._iter_procs(self.res_summary):
                env_result = self.result.modules[mod_name].envs[env_name]
                # 没有统计到内存数据的忽略
                if not (proc.quota and proc.memory):
                    continue

                if proc.quota.limits.memory / proc.memory.max < 2:
                    self.result.issue_type = OperationIssueType.MISCONFIGURED
                    self.result.issues.append(
                        f"平均内存使用率 < 15%，模块 {mod_name} 环境 {env_name} 进程 {proc.name} 内存 Max 值未及 50% Limits",
                    )
                    env_result.issue_type = OperationIssueType.MISCONFIGURED
                    env_result.issues.append(f"进程 {proc.name} 内存 Max 值未及 50% Limits")

    def _evaluate_by_user_visit(self):
        # 无访问记录，说明是不活跃应用
        if not (self.report.pv and self.report.uv):
            self.result.issue_type = OperationIssueType.UNVISITED
            self.result.issues.append(f"应用最近 {self.visit_summary.time_range} 没有访问记录")

        # 环境纬度评估
        for mod_name, mod in self.visit_summary.modules.items():
            for env_name, env in mod.envs.items():
                # 这个环境没有运行中的进程的，跳过
                env_res_summary = self.res_summary.modules[mod_name].envs[env_name]
                if not (env_res_summary.cpu_requests and env_res_summary.mem_requests):
                    continue

                # 有访问记录，跳过
                if env.pv and env.uv:
                    continue

                env_result = self.result.modules[mod_name].envs[env_name]
                env_result.issue_type = OperationIssueType.UNVISITED
                env_result.issues.append(f"该环境最近 {self.visit_summary.time_range} 没有访问记录")

                # 如果没有访问量，且检测到资源使用率基本没有波动，则说明该环境闲置（没有后台任务）
                is_low_cpu_usage, any_proc_running = True, False
                for proc in self.res_summary.modules[mod_name].envs[env_name].procs:
                    if not (proc.quota and proc.cpu):
                        continue

                    any_proc_running = True
                    if proc.cpu.max / proc.quota.limits.cpu > 0.01:
                        is_low_cpu_usage = False
                        break

                if is_low_cpu_usage and any_proc_running:
                    env_result.issues.append(f"CPU 使用率低于 1% 且近 {self.res_summary.time_range} 使用量没有波动")
                    env_result.issue_type = OperationIssueType.IDLE
                    self.result.issue_type = OperationIssueType.IDLE
                    self.result.issues.append(
                        f"模块 {mod_name} 环境 {env_name} 近 {self.visit_summary.time_range} 没有访问记录"
                        + f" 且 近 {self.res_summary.time_range} CPU 使用率低于 1%"
                    )

    def _evaluate_by_process_status(self):
        # 应用纬度
        if not self.report.latest_deployed_at:
            self.result.issues.append("应用未部署过")
            self.result.issue_type = OperationIssueType.UNDEPLOY

        # 注：由于 requests 是根据实际进程数量算出来的，不是理论值，因此如果都是 0 说明没有运行中的进程
        if not self.report.cpu_requests and self.report.mem_requests:
            self.result.issues.append("应用无运行中的进程")
            self.result.issue_type = OperationIssueType.UNDEPLOY

        # 环境纬度评估
        for mod_name, mod in self.deploy_summary.modules.items():
            for env_name, env in mod.envs.items():
                env_result = self.result.modules[mod_name].envs[env_name]
                if not env.latest_deployed_at:
                    env_result.issues.append("该环境没有部署记录")
                    env_result.issue_type = OperationIssueType.UNDEPLOY

                env_res_summary = self.res_summary.modules[mod_name].envs[env_name]
                if not (env_res_summary.cpu_requests and env_res_summary.mem_requests):
                    env_result.issues.append("该环境无运行中的进程")
                    env_result.issue_type = OperationIssueType.UNDEPLOY

    def _evaluate_by_app_members_status(self):
        """根据成员状态评估应用"""
        members = [m["username"] for m in fetch_application_members(self.application.code)]

        # 平台管理员创建的应用，暂不认为是无主应用
        creator = get_username_by_bkpaas_user_id(self.application.creator)
        if creator in settings.BKPAAS_PLATFORM_MANAGERS:
            return

        for m in members:
            if m in settings.BKPAAS_PLATFORM_MANAGERS:
                continue
            if self.staff_status_provider.is_active(m):
                return

        # 对于不是平台管理员创建的应用，如果在职的成员只有管理员，则也认为是无主应用
        self.result.issues.append("应用成员中不包含除平台管理员之外的在职人员")
        self.result.issue_type = OperationIssueType.OWNERLESS

    @staticmethod
    def _iter_procs(res_summary: AppResSummary) -> Generator[Tuple[str, str, ProcResSummary], None, None]:
        """迭代所有的进程"""
        for mod_name, module in res_summary.modules.items():
            for env_name, env in module.envs.items():
                for proc in env.procs:
                    yield mod_name, env_name, proc
