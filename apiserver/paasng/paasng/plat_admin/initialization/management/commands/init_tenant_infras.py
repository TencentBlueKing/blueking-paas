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

import argparse
import json

import yaml
from django.core.management.base import BaseCommand, CommandError

from paasng.plat_admin.initialization.tenant_infras.initializer import (
    Action,
    InitializationError,
    Record,
    TenantInfrasInitializer,
)
from paasng.plat_admin.initialization.tenant_infras.serializers import TenantInfrasSLZ
from paasng.utils.validators import str2bool


class Command(BaseCommand):
    help = (
        "根据 yaml 一键初始化租户的集群、增强服务方案 / 资源池、绑定策略与日志配置，"
        "配置格式参考 paasng/plat_admin/initialization/tenant_infras/example.yaml"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--file", dest="file_", required=True, type=argparse.FileType(), help="租户初始化配置文件路径"
        )
        parser.add_argument(
            "--dry-run", dest="dry_run", default=True, type=str2bool, help="默认只预览变更，传 --dry-run=false 才写入"
        )
        parser.add_argument("--overwrite", action="store_true", help="已存在的数据按配置更新，默认跳过")

    def handle(self, file_, dry_run: bool, overwrite: bool, *args, **options):
        with file_ as fh:
            raw = yaml.safe_load(fh) or {}

        slz = TenantInfrasSLZ(data=raw)
        if not slz.is_valid():
            raise CommandError(f"invalid config: {json.dumps(slz.errors, ensure_ascii=False)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: no data will be written, use --dry-run=false to apply"))

        initializer = TenantInfrasInitializer(
            slz.validated_data, overwrite=overwrite, dry_run=dry_run, on_record=self._print_record
        )
        try:
            initializer.run()
        except InitializationError as e:
            raise CommandError(f"preflight check failed, nothing written: {e}")

        if failed := initializer.failed_records:
            raise CommandError(
                f"{len(failed)} service(s) failed: {', '.join(r.target for r in failed)}, fix and rerun to complete"
            )
        self.stdout.write(self.style.SUCCESS(f"tenant {initializer.tenant_id} initialized"))

    def _print_record(self, record: Record):
        msg = f"[{record.kind}] {record.target}: {record.action}"
        if record.detail:
            msg += f" ({record.detail})"

        if record.action == Action.FAILED:
            self.stderr.write(self.style.ERROR(msg))
        elif record.action == Action.SKIP:
            self.stdout.write(msg)
        else:
            self.stdout.write(self.style.SUCCESS(msg))
