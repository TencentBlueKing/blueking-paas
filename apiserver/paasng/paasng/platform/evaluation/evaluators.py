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
from datetime import timedelta
from typing import Any, Dict, Generator, List, Tuple

from django.conf import settings
from django.utils import timezone

from paasng.infras.iam.helpers import fetch_application_members
from paasng.platform.applications.models import Application
from paasng.platform.evaluation.collectors import AppSummary, ProcSummary
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.providers import StaffStatusProvider
from paasng.utils.basic import get_username_by_bkpaas_user_id


class AppOperationEvaluator:
    """综合各项指标，评估应用运营情况"""

    def __init__(self, app: Application):
        self.app = app
        self.staff_status_provider = StaffStatusProvider()

    def evaluate(self, metrics: Dict[str, Any]) -> Tuple[OperationIssueType, List[str]]:
        """评估应用运营情况"""
        if issues := self._evaluate_by_app_members_status():
            return OperationIssueType.OWNERLESS, issues

        if issues := self._evaluate_by_user_activity(metrics):
            return OperationIssueType.INACTIVE, issues

        if issues := self._evaluate_by_resource_usage(metrics):
            return OperationIssueType.MISCONFIGURED, issues

        return OperationIssueType.NONE, []

    def _evaluate_by_app_members_status(self) -> List[str]:
        """根据成员状态评估应用"""
        members = [m["username"] for m in fetch_application_members(self.app.code)]

        # 平台管理员创建的应用，暂不认为是无主应用
        creator = get_username_by_bkpaas_user_id(self.app.creator)
        if creator in settings.BKPAAS_PLATFORM_MANAGERS:
            return []

        for m in members:
            if m in settings.BKPAAS_PLATFORM_MANAGERS:
                continue
            if self.staff_status_provider.is_active(m):
                return []

        # 对于不是平台管理员创建的应用，如果在职的成员只有管理员，则也认为是无主应用
        return ["应用成员中不包含除平台管理员之外的在职人员"]

    def _evaluate_by_user_activity(self, metrics: Dict[str, Any]) -> List[str]:
        """根据用户活跃度评估应用"""
        # 有访问记录，说明是活跃应用，不需要参与后面的操作评估
        if metrics["pv"] and metrics["uv"]:
            return []

        issues = ["应用最近 30 天没有访问记录"]

        if not metrics["latest_deployed_at"]:
            issues.append("应用未部署过")
        elif metrics["latest_deployed_at"] < timezone.now() - timedelta(days=180):
            issues.append("应用最近半年没有部署记录")

        if not metrics["latest_operated_at"]:
            issues.append("应用没有操作记录")
        elif metrics["latest_operated_at"] < timezone.now() - timedelta(days=90):
            issues.append("应用最近 3 个月没有操作记录")

        return issues

    def _evaluate_by_resource_usage(self, metrics: Dict[str, Any]) -> List[str]:
        """根据资源使用量评估应用"""
        issues = []

        # 平均内存使用率不超过 15% 的，需要检查内存最大使用量，如果不及配额的 1/2，应该提示缩容
        if metrics["mem_usage_avg"] and metrics["mem_usage_avg"] < 0.15:
            for mod, env, proc in self._iter_procs(metrics["res_summary"]):
                # 没有统计到内存数据的忽略
                if not (proc.quota and proc.memory):
                    continue

                if proc.quota.limits.memory / proc.memory.max < 2:
                    issues.append(
                        f"应用平均内存使用率不超过 15%，模块 {mod} 环境 {env} 进程 {proc.name} 内存最大使用量未超过 Limits 的一半",
                    )

        return issues

    @staticmethod
    def _iter_procs(res_summary: AppSummary) -> Generator[Tuple[str, str, ProcSummary], None, None]:
        """迭代所有的进程"""
        for mod in res_summary.modules:
            for env, procs in [("stag", mod.stag_procs), ("prod", mod.prod_procs)]:
                for proc in procs:
                    yield mod.module_name, env, proc
