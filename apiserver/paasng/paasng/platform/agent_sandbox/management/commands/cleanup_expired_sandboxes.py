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

from django.core.management.base import BaseCommand
from django.utils import timezone

from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import delete_sandbox


class Command(BaseCommand):
    """
    Q: 为什么设置了一次最多删除 50 个？
    A: 让删除操作对资源的消耗相对更平稳，也避免定时执行该命令时出现上一次没有删完就又开始了一次的情况
    """

    help = "清理已过期的沙箱实例"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true", help="仅显示将被删除的沙箱，不实际执行删除操作"
        )
        parser.add_argument("--limit", dest="limit", type=int, default=50, help="一次最多删除的沙箱数量，默认50")

    def handle(self, dry_run, limit, *args, **options):
        now = timezone.now()
        base_query = (
            Sandbox.objects.filter(expired_at__isnull=False, expired_at__lte=now)
            .exclude(status__in=[SandboxStatus.DELETED.value, SandboxStatus.ERR_DELETING.value])
            .select_related("application")
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

        for idx, sandbox in enumerate(query):
            delete_sandbox(sandbox)
            self.stdout.write(
                f"已删除 {idx + 1}/{total} uuid={sandbox.uuid} name={sandbox.name} app_code={sandbox.application.code}"
            )

        self.stdout.write(f"\n清理完成: 删除 {total} 个")
