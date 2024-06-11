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
from django.dispatch import receiver

from paasng.platform.applications.signals import module_environment_offline_success
from paasng.platform.engine.models import OfflineOperation
from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport


@receiver(module_environment_offline_success)
def on_environment_offline_succeed(sender, offline_instance: OfflineOperation, environment: str, **kwargs):
    """如果某个环境被下架，且运营报告存在，需要及时更新运营报告中该环境的评估结果（避免下架后还出现在闲置应用列表中）"""
    module_env = offline_instance.app_environment
    report = AppOperationReport.objects.filter(app=module_env.application).first()
    if not report:
        return

    # 更新应用评估状态
    mod_name, env_name = module_env.module.name, environment
    if mod_name in report.evaluate_result["modules"]:  # noqa: SIM102
        if env_name in report.evaluate_result["modules"][mod_name]["envs"]:
            report.evaluate_result["modules"][mod_name]["envs"][env_name]["issue_type"] = OperationIssueType.UNDEPLOY
            report.save(update_fields=["evaluate_result"])
