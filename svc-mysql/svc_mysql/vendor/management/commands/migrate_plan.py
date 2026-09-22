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

"""在 plan 之间迁移 MySQL 实例。实例 uuid 保持不变，迁移期间应用仍使用旧库。

使用方式:
    python manage.py migrate_plan prepare -a <app_code> -t <目标 plan 名称> [-m <模块>] [-e stag|prod] [-d <developer>]
    python manage.py migrate_plan switch  -a <app_code> [-m <模块>] [-e stag|prod]
    python manage.py migrate_plan revert  -a <app_code> [-m <模块>] [-e stag|prod]
    python manage.py migrate_plan status  [-a <app_code>] [-m <模块>] [-e stag|prod]

prepare 在目标 plan 上预分配新库，标准输出是给运维复制的连接信息（不含密码）。
运维完成数据同步后执行 switch，再重新部署应用。revert 把绑定写回旧库，目标库保留。
"""

from django.core.management.base import BaseCommand, CommandError

from svc_mysql.vendor.plan_migration import (
    MigrationScope,
    prepare_migrations,
    query_migrations,
    render_copy_blocks,
    render_status,
    resolve_target_plan,
    revert_migrations,
    switch_migrations,
)

DEFAULT_ENVIRONMENTS = ["stag", "prod"]


class Command(BaseCommand):
    help = "在 plan 之间迁移 MySQL 实例，实例 uuid 保持不变。"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)
        self._add_prepare(subparsers)
        self._add_switch(subparsers)
        self._add_revert(subparsers)
        self._add_status(subparsers)

    def handle(self, **options):
        action = options["action"]
        handlers = {
            "prepare": self._prepare,
            "switch": self._switch,
            "revert": self._revert,
            "status": self._status,
        }
        handlers[action](options)

    def _prepare(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=True)
        target_plan = resolve_target_plan(options["target_plan"])
        developer = options.get("developer") or ""
        sections, skipped, failures = prepare_migrations(scope, target_plan, developer)
        for message in skipped:
            self.stderr.write(message + "\n")
        if sections:
            self.stdout.write(render_copy_blocks(sections, developer))
        self.stderr.write(f"预分配完成 {len(sections)} 条，跳过 {len(skipped)} 条\n")
        if failures:
            raise CommandError(f"以下实例预分配失败: {', '.join(failures)}")

    def _switch(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=True)
        result = switch_migrations(scope)
        for label in result.labels:
            self.stdout.write(f"已切换 {label}，请重新部署后使用新库\n")
        if result.failures:
            raise CommandError(f"以下实例切换失败: {', '.join(result.failures)}")

    def _revert(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=True)
        result = revert_migrations(scope)
        for label in result.labels:
            self.stdout.write(f"已回切 {label}，请重新部署后使用旧库\n")
        if result.failures:
            raise CommandError(f"以下实例回切失败: {', '.join(result.failures)}")

    def _status(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=False)
        self.stdout.write(render_status(query_migrations(scope)))

    def _add_prepare(self, subparsers) -> None:
        parser = subparsers.add_parser("prepare", help="在目标 plan 上预分配数据库")
        _add_scope(parser, app_required=True)
        parser.add_argument("-t", "--target-plan", dest="target_plan", required=True, help="目标 plan 名称")
        parser.add_argument("-d", "--developer", dest="developer", default="", help="开发者，不传则留空")

    def _add_switch(self, subparsers) -> None:
        parser = subparsers.add_parser("switch", help="把已预分配的实例切换到目标库")
        _add_scope(parser, app_required=True)

    def _add_revert(self, subparsers) -> None:
        parser = subparsers.add_parser("revert", help="把已切换的实例写回旧库")
        _add_scope(parser, app_required=True)

    def _add_status(self, subparsers) -> None:
        parser = subparsers.add_parser("status", help="查看迁移状态")
        _add_scope(parser, app_required=False)


def _add_scope(parser, *, app_required: bool) -> None:
    parser.add_argument("-a", "--app-code", dest="app_code", required=app_required, help="应用 ID")
    parser.add_argument(
        "-m",
        "--module",
        dest="modules",
        action="append",
        default=None,
        help="模块名，可重复。不传则处理范围内所有已绑定 MySQL 的模块",
    )
    parser.add_argument(
        "-e",
        "--environment",
        dest="environments",
        action="append",
        choices=["stag", "prod"],
        default=None,
        help="环境，可重复。prepare/switch/revert 不传则包含 stag 和 prod；status 不传则不过滤",
    )


def _scope_from_options(options: dict, *, default_environments: bool) -> MigrationScope:
    environments = options.get("environments")
    if default_environments and not environments:
        environments = list(DEFAULT_ENVIRONMENTS)
    return MigrationScope(
        app_code=options.get("app_code") or "",
        modules=options.get("modules"),
        environments=environments,
    )
