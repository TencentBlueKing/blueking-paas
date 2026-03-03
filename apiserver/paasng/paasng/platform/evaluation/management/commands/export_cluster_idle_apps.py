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

"""导出指定集群上所有的闲置应用到 excel 文件

Examples:
    python manage.py export_cluster_idle_apps --cluster cluster-name
"""

import logging
from datetime import datetime
from typing import List

import xlwt
from django.core.management.base import BaseCommand

from paasng.platform.evaluation.constants import OperationIssueType
from paasng.platform.evaluation.models import AppOperationReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export idle applications in specified cluster"

    def add_arguments(self, parser):
        parser.add_argument("--cluster", dest="cluster", required=True, help="Cluster name")

    def handle(self, *args, **options):
        cluster_name = options["cluster"]
        self.stdout.write(f"Starting to filter idle applications on cluster {cluster_name}...")

        # 查询所有闲置应用报告（issue_type 为 idle）
        idle_reports = AppOperationReport.objects.filter(issue_type=OperationIssueType.IDLE)

        # 筛选属于指定集群的应用
        filtered_reports = []
        for report in idle_reports:
            if self.is_app_in_cluster(report.app, cluster_name):
                filtered_reports.append(report)

        self.stdout.write(f"Found {len(filtered_reports)} idle applications")

        # 导出到 Excel
        file_path = self.export_to_excel(filtered_reports, cluster_name)
        self.stdout.write(self.style.SUCCESS(f"Export completed, file path: {file_path}"))

    @staticmethod
    def is_app_in_cluster(app, cluster_name: str) -> bool:
        """判断应用是否部署在指定集群上

        遍历应用的所有模块和环境，通过 env.engine_app.to_wl_obj() 获取 wl_app，
        再通过 get_cluster_by_app 获取集群信息，判断是否属于指定集群。

        :param app: Application 对象
        :param cluster_name: 目标集群名称
        :return: 如果应用的任意模块/环境部署在指定集群上，返回 True
        """
        try:
            for module in app.modules.all():
                for env in module.envs.all():
                    try:
                        wl_app = env.engine_app.to_wl_obj()
                        if wl_app.latest_config.cluster == cluster_name:
                            return True
                    except Exception as e:
                        logger.warning(
                            f"Failed to get cluster info for app {app.code} "
                            f"module {module.name} environment {env.environment}: {e}"
                        )
                        continue
        except Exception as e:
            logger.warning(f"Exception occurred while determining cluster for app {app.code}: {e}")
        return False

    @staticmethod
    def get_sheet_headers() -> List[str]:
        """获取 Excel 表头"""
        return [
            "应用 Code",
            "应用名称",
            "内存 Requests",
            "内存 Limits",
            "内存使用率（7d）",
            "CPU Requests",
            "CPU Limits",
            "CPU 使用率（7d）",
            "PV（30d）",
            "UV（30d）",
            "最新操作人",
            "最新操作时间",
            "问题类型",
            "问题描述",
            "应用管理员",
        ]

    @staticmethod
    def get_sheet_data(reports: List[AppOperationReport]) -> List[List[str]]:
        """获取 Excel 数据行

        :param reports: 筛选后的应用报告列表
        :return: 数据行列表
        """
        rows = []
        for rp in reports:
            try:
                administrators = ", ".join(rp.app.get_administrators())
            except Exception:  # noqa
                administrators = "--"

            rows.append(
                [
                    rp.app.code,
                    rp.app.name,
                    f"{round(rp.mem_requests / 1024, 2)} G",
                    f"{round(rp.mem_limits / 1024, 2)} G",
                    f"{round(rp.mem_usage_avg * 100, 2)}%",
                    f"{round(rp.cpu_requests / 1000, 2)} 核",
                    f"{round(rp.cpu_limits / 1000, 2)} 核",
                    f"{round(rp.cpu_usage_avg * 100, 2)}%",
                    str(rp.pv),
                    str(rp.uv),
                    rp.latest_operator if rp.latest_operator else "--",
                    rp.latest_operated_at.strftime("%Y-%m-%d %H:%M:%S") if rp.latest_operated_at else "--",
                    str(OperationIssueType.get_choice_label(rp.issue_type)),
                    ", ".join(rp.evaluate_result["issues"]) if rp.evaluate_result else "--",
                    administrators,
                ]
            )

        return rows

    def export_to_excel(self, reports: List[AppOperationReport], cluster_name: str) -> str:
        """导出报告到 Excel 文件

        :param reports: 筛选后的应用报告列表
        :param cluster_name: 集群名称（用于生成文件名）
        :return: 生成的文件路径
        """
        work_book = xlwt.Workbook(encoding="utf-8")
        work_sheet = work_book.add_sheet("reports")

        # 写入表头
        sheet_headers = self.get_sheet_headers()
        for idx, value in enumerate(sheet_headers):
            work_sheet.col(idx).width = 256 * 20
            work_sheet.write(0, idx, value)

        # 写入数据
        sheet_data = self.get_sheet_data(reports)
        for row_num, values in enumerate(sheet_data, start=1):
            for col_num, val in enumerate(values):
                work_sheet.write(row_num, col_num, val)

        # 生成文件名（包含集群名称和时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"idle_apps_{cluster_name}_{timestamp}.xls"
        work_book.save(file_name)

        return file_name
