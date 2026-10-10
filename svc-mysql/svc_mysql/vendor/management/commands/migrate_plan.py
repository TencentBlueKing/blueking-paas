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

仅适用于单租户环境。目标 plan 只按名称查找，多租户不在支持范围内。

先在本服务执行 prepare / switch。切换后到 apiserver 执行 migrate_mysql_plan
把环境绑定上的 plan 改成目标方案，再重新部署。switch 之后迁移即完成，仍可 revert。
apiserver 不会回滚 plan。

使用说明:
    不传 --module 时处理范围内所有已绑定 MySQL 的模块。
    不传 --environment 时 prepare、switch、revert 处理 stag 和 prod。
    --developer 是这个实例的联系人，不传则留空。再次 prepare 时以最新一次为准。
    还没开通的环境这里没有实例，要靠 apiserver 命令切绑定 plan，下次部署才会用目标 plan。
    源库由运维在切换后确认没有连接再删除，本命令不删库。源库删除后不要再 revert。

使用示例:
    # 预分配 stag 和 prod。标准输出是给运维复制的连接信息，不含密码
    python manage.py migrate_plan prepare --app-code <app_code> --target-plan mysql-8.0 --developer <contact>

    # 只处理指定模块和环境。--module、--environment 都可以重复
    python manage.py migrate_plan prepare --app-code <app_code> --target-plan mysql-8.0 \
        --module default --module api --environment prod

    # 查看全部迁移记录，或按状态筛选
    python manage.py migrate_plan status
    python manage.py migrate_plan status --status switched

    # 运维同步完数据后切换，然后到 apiserver 改绑定 plan，再重新部署
    python manage.py migrate_plan switch --app-code <app_code> --module default --environment prod

    # 切换后有问题，写回旧库。目标库保留，需要再部署一次
    python manage.py migrate_plan revert --app-code <app_code> --module default --environment prod
"""

import base64

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
    help = "在 plan 之间迁移 MySQL 实例，实例 uuid 保持不变。仅适用于单租户环境。"

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
            block = render_copy_blocks(sections, developer)
            self.stdout.write(block)
            # 可见文本在前，剪贴板只放这段，不含下面的提示。
            self.stdout.write(_wrap_osc52(block))
        self.stderr.write(f"预分配完成 {len(sections)} 条，跳过 {len(skipped)} 条\n")
        self.stderr.write(
            "下一步：把标准输出里的连接信息交给运维同步数据。同步完成后执行 "
            f"migrate_plan switch --app-code {scope.app_code} 。切换后到 apiserver 执行 "
            f"migrate_mysql_plan --app-code {scope.app_code} --target-plan {target_plan.name} ，"
            "再重新部署。\n"
        )
        if failures:
            raise CommandError(f"以下实例预分配失败: {', '.join(failures)}")

    def _switch(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=True)
        result = switch_migrations(scope)
        for label in result.labels:
            self.stdout.write(f"已切换 {label}，请重新部署后使用新库\n")
        if result.labels:
            self.stderr.write(
                "下一步：到 apiserver 执行 "
                f"migrate_mysql_plan --app-code {scope.app_code} --target-plan <目标 plan 名称> ，"
                "把环境绑定的 plan 改成与实例一致，然后重新部署应用。\n"
            )
        if result.failures:
            raise CommandError(f"以下实例切换失败: {', '.join(result.failures)}")

    def _revert(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=True)
        result = revert_migrations(scope)
        for label in result.labels:
            self.stdout.write(f"已回切 {label}，请重新部署后使用旧库\n")
        if result.labels:
            self.stderr.write(
                "下一步：重新部署应用，使旧库生效。apiserver 的绑定 plan 不会跟着回滚；"
                "如果已经执行过 migrate_mysql_plan，需要手工改回源 plan，否则下次部署会因 plan 不一致失败。\n"
            )
        if result.failures:
            raise CommandError(f"以下实例回切失败: {', '.join(result.failures)}")

    def _status(self, options: dict) -> None:
        scope = _scope_from_options(options, default_environments=False)
        self.stdout.write(render_status(query_migrations(scope)))

    def _add_prepare(self, subparsers) -> None:
        parser = subparsers.add_parser("prepare", help="在目标 plan 上预分配数据库")
        _add_scope(parser, app_required=True)
        parser.add_argument("--target-plan", dest="target_plan", required=True, help="目标 plan 名称")
        parser.add_argument("--developer", dest="developer", default="", help="联系人，不传则留空")

    def _add_switch(self, subparsers) -> None:
        parser = subparsers.add_parser("switch", help="把已预分配的实例切换到目标库")
        _add_scope(parser, app_required=True)

    def _add_revert(self, subparsers) -> None:
        parser = subparsers.add_parser("revert", help="把已切换的实例写回旧库")
        _add_scope(parser, app_required=True)

    def _add_status(self, subparsers) -> None:
        parser = subparsers.add_parser("status", help="查看迁移状态。不传应用时列出全部记录")
        _add_scope(parser, app_required=False)
        parser.add_argument(
            "--status",
            dest="status",
            choices=["prepared", "switched", "superseded"],
            default=None,
            help=(
                "按状态筛选，不传则不过滤。"
                "prepared：目标库已建好，应用仍用旧库，等运维同步数据后 switch；"
                "switched：实例已指向目标库，迁移完成，需要时仍可 revert 回旧库；"
                "superseded：同一实例已开始下一轮迁移，这条记录被取代，不能再 revert"
            ),
        )


def _add_scope(parser, *, app_required: bool) -> None:
    parser.add_argument("--app-code", dest="app_code", required=app_required, help="应用 ID")
    parser.add_argument(
        "--module",
        dest="modules",
        action="append",
        default=None,
        help="模块名，可重复。不传则处理范围内所有已绑定 MySQL 的模块",
    )
    parser.add_argument(
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
        status=options.get("status"),
    )


def _wrap_osc52(text: str) -> str:
    """把文本放进终端剪贴板。终端不支持时忽略这段转义序列。"""
    encoded = base64.b64encode(text.encode()).decode()
    return f"\033]52;c;{encoded}\a"
