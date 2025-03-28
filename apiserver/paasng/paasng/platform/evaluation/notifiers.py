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
import logging
from typing import List, Tuple

import arrow
import humanize
from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from django.db.models import QuerySet
from django.template import loader
from django.utils import timezone

from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.evaluation.constants import EmailReceiverType, OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport, IdleAppNotificationMuteRule
from paasng.utils import dictx
from paasng.utils.notifier import get_notification_backend

logger = logging.getLogger(__name__)


class AppOperationReportNotifier:
    """将蓝鲸应用的运营报告发送到指定对象"""

    def send(
        self,
        reports: QuerySet[AppOperationReport],
        receiver_type: EmailReceiverType,
        receivers: List[str],
    ):
        if not reports.exists():
            logger.info("no issue reports, skip notification...")
            return

        if not receivers:
            logger.warning("not receivers, skip notification...")
            return

        if receiver_type == EmailReceiverType.PLAT_ADMIN:
            title, content = self._gen_plat_admin_email_title_and_content(reports)
        elif receiver_type == EmailReceiverType.APP_DEVELOPER:
            if len(receivers) != 1:
                raise ValueError("notify to app developers only support one by one")

            title, content = self._gen_app_developers_email_title_and_content(reports, receivers[0])
        else:
            raise ValueError(f"unknown receiver type: {receiver_type}")

        if not (title and content):
            logger.info("no title or content, skip notification...")
            return

        get_notification_backend().mail.send(receivers, content, title)

    def _gen_plat_admin_email_title_and_content(self, reports: QuerySet[AppOperationReport]) -> Tuple[str, str]:
        title = "蓝鲸开发者中心 - 应用运营异常关注通知"
        tmpl_name = "email_templates/send_operation_summary_to_plat_manager.html"

        context = {
            "bkpaas_url": settings.BKPAAS_URL,
            "ownerless_cnt": reports.filter(issue_type=OperationIssueType.OWNERLESS).count(),
            "idle_cnt": reports.filter(issue_type=OperationIssueType.IDLE).count(),
            "unvisited_cnt": reports.filter(issue_type=OperationIssueType.UNVISITED).count(),
            "maintainless_cnt": reports.filter(issue_type=OperationIssueType.MAINTAINLESS).count(),
            "undeploy_cnt": reports.filter(issue_type=OperationIssueType.UNDEPLOY).count(),
            "misconfigured_cnt": reports.filter(issue_type=OperationIssueType.MISCONFIGURED).count(),
        }
        return title, loader.render_to_string(tmpl_name, context)

    def _gen_app_developers_email_title_and_content(
        self, reports: QuerySet[AppOperationReport], receiver: str
    ) -> Tuple[str, str]:
        title_tmpl = "蓝鲸开发者中心 - {} 个闲置蓝鲸应用模块待处理"
        tmpl_name = "email_templates/send_idle_module_envs_to_developer.html"

        mute_rules = {
            (r.app_code, r.module_name, r.environment)
            for r in IdleAppNotificationMuteRule.objects.filter(
                user=user_id_encoder.encode(username=receiver, provider_type=settings.USER_TYPE),
                expired_at__gt=timezone.now(),
            )
        }

        # 切换时间差成中文展示
        humanize.i18n.activate("zh_cn")
        time_now = arrow.now()

        idle_apps = []
        for r in reports:
            idle_module_envs = []

            for module_name, mod_evaluate_result in r.evaluate_result["modules"].items():
                for env_name, env_evaluate_result in mod_evaluate_result["envs"].items():
                    if env_evaluate_result["issue_type"] != OperationIssueType.IDLE:
                        continue
                    # 已经设置屏蔽提醒的需要跳过
                    if (r.app.code, module_name, env_name) in mute_rules:
                        continue

                    path = f"modules.{module_name}.envs.{env_name}"
                    env_res_summary = dictx.get_items(r.res_summary, path)
                    env_deploy_summary = dictx.get_items(r.deploy_summary, path)

                    cpu_quota = round(env_res_summary["cpu_limits"] / 1000, 2)
                    mem_quota = round(env_res_summary["mem_limits"] / 1024, 2)

                    idle_module_envs.append(
                        {
                            "module_name": module_name,
                            "environment": AppEnvironment.get_choice_label(env_name),
                            "res_summary": f"{mem_quota}G / {cpu_quota} 核",
                            "cpu_usage_avg": f"{round(env_res_summary['cpu_usage_avg'] * 100, 2)}%",
                            "latest_deployed_at": humanize.naturaltime(
                                time_now - arrow.get(env_deploy_summary["latest_deployed_at"])
                            ),
                        }
                    )

            if not idle_module_envs:
                continue

            idle_apps.append({"name": r.app.name, "code": r.app.code, "module_envs": idle_module_envs})

        humanize.i18n.deactivate()

        # 由于允许屏蔽通知，是有可能最后发现没有需要通知的应用的情况的
        if not idle_apps:
            return "", ""

        context = {"bkpaas_url": settings.BKPAAS_URL, "idle_cnt": len(idle_apps), "idle_apps": idle_apps}
        return title_tmpl.format(len(idle_apps)), loader.render_to_string(tmpl_name, context)
