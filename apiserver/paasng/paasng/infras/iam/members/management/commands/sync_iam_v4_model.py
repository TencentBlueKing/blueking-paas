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

from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError

from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.iam.exceptions import InvalidIAMIdentifierError
from paasng.infras.iam.v4.definitions import resolve_system_definitions
from paasng.infras.iam.v4.registry import AggregatedSyncResult, ModelSyncResult, SyncItem, sync_iam_v4_models


class Command(BaseCommand):
    """把 bk_paas3 / bk_plugins 的权限模型幂等同步到 IAM V4

    使用示例：
    python manage.py sync_iam_v4_model
    python manage.py sync_iam_v4_model --system paas
    python manage.py sync_iam_v4_model --system plugins --dry-run

    请求头中的租户标识与 V3 模型 migration 一致，由 get_init_tenant_id() 决定：
    多租户为 system，非多租户为 default。模型注册是平台级初始化，不按业务租户拆分。
    """

    help = "将开发者中心与插件中心的权限模型同步到 IAM V4（只新增/更新，多余项告警）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--system",
            dest="systems",
            action="append",
            help="要同步的系统，可重复指定。取值：paas / plugins，或配置中的系统 ID。默认同步两个系统",
        )
        parser.add_argument("--dry-run", action="store_true", help="只输出将要执行的差异，不写入 V4")

    def handle(self, systems: Optional[List[str]], dry_run: bool, *args, **options):
        try:
            definitions = resolve_system_definitions(systems)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        try:
            result = sync_iam_v4_models(definitions, tenant_id=get_init_tenant_id(), dry_run=dry_run)
        except InvalidIAMIdentifierError as exc:
            self.stderr.write(self.style.ERROR("标识符不满足 IAM V4 命名约束，未向 V4 提交任何请求："))
            for identifier in exc.identifiers:
                self.stderr.write(f"  - {identifier}")
            raise CommandError(str(exc)) from exc

        self._print_result(result, dry_run)
        if result.has_failures:
            raise CommandError(
                f"模型同步存在失败项: 新增={result.created_count} 更新={result.updated_count} "
                f"告警={result.warning_count} 失败={result.failure_count}"
            )

    def _print_result(self, aggregated: AggregatedSyncResult, dry_run: bool):
        prefix = "[dry-run] " if dry_run else ""
        for result in aggregated.results:
            self._print_system_result(result, prefix)

        counts = aggregated.counts()
        self.stdout.write(
            self.style.NOTICE(
                f"{prefix}合计: 新增={counts['created']} 更新={counts['updated']} "
                f"告警={counts['warnings']} 失败={counts['failures']}"
            )
        )

    def _print_system_result(self, result: ModelSyncResult, prefix: str):
        counts = result.counts()
        self.stdout.write(
            f"{prefix}系统 {result.system_id}: 新增={counts['created']} 更新={counts['updated']} "
            f"告警={counts['warnings']} 失败={counts['failures']}"
        )
        self._print_items("+", result.created)
        self._print_items("*", result.updated)
        self._print_items("!", result.warnings, style=self.style.WARNING)
        self._print_items("x", result.failures, style=self.style.ERROR, with_request_id=True)

    def _print_items(
        self,
        mark: str,
        items: List[SyncItem],
        style=None,
        with_request_id: bool = False,
    ):
        for item in items:
            line = f"  {mark} [{item.kind}] {item.identifier}"
            if item.detail:
                line = f"{line} - {item.detail}"
            if with_request_id and item.request_id:
                line = f"{line} (iam request_id: {item.request_id})"
            self.stdout.write(style(line) if style else line)
