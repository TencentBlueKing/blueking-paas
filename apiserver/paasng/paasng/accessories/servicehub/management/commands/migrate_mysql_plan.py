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

"""把 MySQL 环境绑定的 plan 改成目标方案。不回滚。

先在 svc-mysql 执行 migrate_plan prepare / switch。本命令不搬数据库。
未开通的环境会直接改绑定；已开通的环境要等实例 plan 已经是目标方案。

使用示例:
    python manage.py migrate_mysql_plan -a <app_code> -t mysql-8.0
    python manage.py migrate_mysql_plan -a <app_code> -t mysql-8.0 -m default -e prod
"""

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from paasng.accessories.servicehub.mysql_plan_migration import align_mysql_plans

DEFAULT_ENVIRONMENTS = ["stag", "prod"]


class Command(BaseCommand):
    help = "把 MySQL 环境绑定的 plan 改成目标方案。先执行 svc-mysql 的 migrate_plan。"

    def add_arguments(self, parser):
        parser.add_argument("-a", "--app-code", dest="app_code", required=True, help="应用 ID")
        parser.add_argument("-t", "--target-plan", dest="target_plan", required=True, help="目标 plan 名称")
        parser.add_argument(
            "-m",
            "--module",
            dest="modules",
            action="append",
            default=None,
            help="模块名，可重复。不传则处理应用下所有模块",
        )
        parser.add_argument(
            "-e",
            "--environment",
            dest="environments",
            action="append",
            choices=DEFAULT_ENVIRONMENTS,
            default=None,
            help="环境，可重复。不传则包含 stag 和 prod",
        )

    def handle(self, **options):
        environments = options.get("environments") or list(DEFAULT_ENVIRONMENTS)
        try:
            outcome = align_mysql_plans(
                options["app_code"],
                options["target_plan"],
                options.get("modules"),
                environments,
            )
        except (LookupError, ObjectDoesNotExist) as exc:
            raise CommandError(str(exc)) from exc

        for message in outcome.updated:
            self.stdout.write(message + "\n")
        for message in outcome.skipped:
            self.stderr.write(message + "\n")
        self.stderr.write(f"绑定已更新 {len(outcome.updated)} 条，跳过 {len(outcome.skipped)} 条\n")
        if outcome.updated:
            self.stderr.write("下一步：重新部署应用。\n")
