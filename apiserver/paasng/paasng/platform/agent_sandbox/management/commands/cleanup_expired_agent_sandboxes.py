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

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.exceptions import SandboxError
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import delete_sandbox

DEFAULT_CLEANUP_CONCURRENCY = 20


def expired_sandbox_queryset(now):
    return (
        Sandbox.objects.filter(expired_at__isnull=False, expired_at__lte=now)
        .exclude(status__in=[SandboxStatus.DELETED.value, SandboxStatus.ERR_DELETING.value])
        .select_related("application")
        .order_by("expired_at")
    )


@dataclass
class _DeleteResult:
    success: bool
    sandbox: Sandbox
    error: SandboxError | None = None


def _delete_expired_sandbox(sandbox_uuid: uuid.UUID) -> _DeleteResult:
    close_old_connections()
    sandbox = Sandbox.objects.select_related("application").get(uuid=sandbox_uuid)
    try:
        delete_sandbox(sandbox)
    except SandboxError as exc:
        return _DeleteResult(success=False, sandbox=sandbox, error=exc)
    return _DeleteResult(success=True, sandbox=sandbox)


class Command(BaseCommand):
    help = "清理已过期的沙箱实例"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true", help="仅显示将被删除的沙箱，不实际执行删除操作"
        )
        parser.add_argument(
            "--concurrency",
            dest="concurrency",
            type=int,
            default=DEFAULT_CLEANUP_CONCURRENCY,
            help=f"并发删除的沙箱数量，默认 {DEFAULT_CLEANUP_CONCURRENCY}",
        )

    def handle(self, dry_run, concurrency, *args, **options):
        if concurrency < 1:
            self.stderr.write(self.style.ERROR("concurrency 必须大于 0"))
            return

        now = timezone.now()
        sandboxes = expired_sandbox_queryset(now)
        total = sandboxes.count()

        self.stdout.write(f"共找到 {total} 个过期沙箱待清理")

        if total == 0:
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run 模式：仅显示，不实际删除"))
            for sandbox in sandboxes:
                self.stdout.write(
                    f"uuid={sandbox.uuid} name={sandbox.name} app_code={sandbox.application.code} "
                    f"expired_at={sandbox.expired_at:%Y-%m-%d %H:%M:%S}"
                )
            return

        sandbox_uuids = list(sandboxes.values_list("uuid", flat=True))
        deleted_count = 0
        failed_count = 0
        output_lock = threading.Lock()
        workers = min(concurrency, len(sandbox_uuids))

        self.stdout.write(f"并发数: {workers}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_delete_expired_sandbox, sbx_uuid) for sbx_uuid in sandbox_uuids]
            for future in as_completed(futures):
                result = future.result()
                with output_lock:
                    if result.success:
                        deleted_count += 1
                        self.stdout.write(
                            f"已删除 {deleted_count}/{total} uuid={result.sandbox.uuid} "
                            f"name={result.sandbox.name} app_code={result.sandbox.application.code}"
                        )
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"删除失败 uuid={result.sandbox.uuid} name={result.sandbox.name} "
                                f"app_code={result.sandbox.application.code}: {result.error}"
                            )
                        )

        self.stdout.write(f"\n清理完成: 删除 {deleted_count} 个, 失败 {failed_count} 个")
