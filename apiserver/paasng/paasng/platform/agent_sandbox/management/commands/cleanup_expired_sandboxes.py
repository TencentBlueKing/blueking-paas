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

"""清理过期的沙箱实例"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import delete_sandbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "清理已过期的沙箱实例"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true", help="仅显示将被删除的沙箱，不实际执行删除操作"
        )
        parser.add_argument("--limit", dest="limit", type=int, default=100, help="一次最多删除的沙箱数量，默认100")

    def handle(self, dry_run, limit, *args, **options):
        now = timezone.now()
        base_query = Sandbox.objects.filter(expired_at__isnull=False, expired_at__lte=now).exclude(
            status__in=[SandboxStatus.DELETED.value, SandboxStatus.ERR_DELETING.value]
        )

        total_all = base_query.count()
        query = base_query.order_by("expired_at")[:limit]
        total = query.count()

        self.stdout.write(f"共找到 {total_all} 个过期沙箱，本次处理 {total} 个")

        if total == 0:
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run 模式：仅显示，不实际删除"))
            for sandbox in query:
                self.stdout.write(
                    f"uuid={sandbox.uuid} name={sandbox.name} app_code={sandbox.application.code} expired_at={sandbox.expired_at:%Y-%m-%d %H:%M:%S}"
                )
            return

        deleted_count = 0
        error_count = 0

        for idx, sandbox in enumerate(query, start=1):
            try:
                logger.info(f"开始删除过期沙箱: {sandbox.uuid} ({sandbox.name})")
                delete_sandbox(sandbox)
                deleted_count += 1
                self.stdout.write(
                    f"[{idx}/{total}] [OK] 已删除沙箱: {sandbox.uuid} (应用: {sandbox.application.code}, 名称: {sandbox.name})"
                )
            except Exception as e:
                error_count += 1
                logger.exception(f"删除沙箱 {sandbox.uuid} 失败")
                self.stdout.write(f"[FAIL] 删除失败: {sandbox.uuid} - {e}")

        self.stdout.write(f"\n清理完成: 成功删除 {deleted_count} 个，失败 {error_count} 个")
