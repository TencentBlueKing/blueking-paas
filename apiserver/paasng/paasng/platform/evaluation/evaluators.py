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
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.utils import timezone

from paasng.infras.iam.helpers import fetch_application_members
from paasng.platform.applications.models import Application
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.providers import EmployeeStatusProvider
from paasng.utils.basic import get_username_by_bkpaas_user_id


class AppOperationEvaluator:
    """综合各项指标，评估应用运营情况"""

    def __init__(self, app: Application):
        self.app = app
        self.employee_status_provider = EmployeeStatusProvider()

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

        # 应用成员为空，妥妥的无主应用
        if not members:
            return ["应用成员列表为空"]

        # 检查应用成员中，非平台管理员的，是否有在职的
        for m in members:
            if m in settings.BKPAAS_PLATFORM_MANAGERS:
                continue
            if self.employee_status_provider.is_active_employee(m):
                return []

        creator = get_username_by_bkpaas_user_id(self.app.creator)
        # 前面步骤检查了所有非平台管理员的成员是否在职，若都不在职，且创建者不是平台管理员，则认为是无主应用
        if creator not in settings.BKPAAS_PLATFORM_MANAGERS:
            return ["应用创建者不是平台管理员，但在职的应用成员都是平台管理员"]

        return []

    def _evaluate_by_user_activity(self, metrics: Dict[str, Any]) -> List[str]:
        """根据用户活跃度评估应用"""
        issues = []

        if not (metrics["pv"] and metrics["uv"]):
            issues.append("应用最近 30 天没有访问记录")

        if not metrics["last_deployed_at"]:
            issues.append("应用未部署过")
        elif metrics["last_deployed_at"] < timezone.now() - timedelta(days=180):
            issues.append("应用最近半年没有部署记录")

        if not metrics["last_operated_at"]:
            issues.append("应用没有操作记录")
        elif metrics["last_operated_at"] < timezone.now() - timedelta(days=90):
            issues.append("应用最近 3 个月没有操作记录")

        return issues

    def _evaluate_by_resource_usage(self, metrics: Dict[str, Any]) -> List[str]:
        """根据资源使用量评估应用"""
        issues = []

        # 平均内存使用率不超过 15% 的，需要检查内存最大使用量，如果不及配额的 1/2，应该提示缩容
        if metrics["mem_usage_avg"] and metrics["mem_usage_avg"] < 0.15:
            for mod in metrics["res_summary"].modules:
                for env, procs in [("stag", mod.stag_procs), ("prod", mod.prod_procs)]:
                    for proc in procs:
                        # 没有统计到内存数据的忽略
                        if not (proc.quota and proc.memory):
                            continue

                        if proc.quota.limits.memory / proc.memory.max < 2:
                            issues.append(
                                "应用平均内存使用率不超过 15%，"
                                f"模块 {mod.module_name} 环境 {env} 进程 {proc.name} "
                                "内存最大使用量未超过 Limits 的一半"
                            )

        return issues
