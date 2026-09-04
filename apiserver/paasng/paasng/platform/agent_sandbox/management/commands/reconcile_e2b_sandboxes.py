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

"""手动触发 e2b 沙箱状态对账。

常规运行由调度器按周期驱动（``scheduler/jobs.py``），这个命令是给运维用的：
上线前先 ``--dry-run`` 看清理范围，或在某集群恢复后立刻补一轮，不必等下个周期。
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from paasng.platform.agent_sandbox.e2b.reconcile import archive_terminated_sandboxes, reconcile_all


class Command(BaseCommand):
    help = "对账 e2b 沙箱的本地状态与网关实际状态，并清理孤儿实例与过期记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="只统计不写入，用于确认将要销毁与删除的范围",
        )
        parser.add_argument(
            "--skip-archive",
            dest="skip_archive",
            action="store_true",
            help="只做状态对账，不删除过期的终止记录",
        )

    def handle(self, dry_run, skip_archive, *args, **options):
        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run 模式：不会销毁任何沙箱，也不会删除任何记录"))
        if not settings.AGENT_SANDBOX_E2B_ORPHAN_CLEANUP_ENABLED:
            self.stdout.write(self.style.WARNING("孤儿清理已被配置关闭，本次只做状态收敛"))

        result = reconcile_all(dry_run=dry_run)

        self.stdout.write(f"对账集群: 成功 {result.clusters_done} 个, 跳过 {result.clusters_skipped} 个")
        if result.skipped_cluster_names:
            self.stdout.write(
                self.style.ERROR(f"跳过的集群（网关不可达或未登记配置）: {', '.join(result.skipped_cluster_names)}")
            )
        self.stdout.write(f"状态收敛: {result.converged} 条")
        self.stdout.write(f"孤儿实例: 销毁 {result.orphans_killed} 个, 观察中 {result.orphans_waiting} 个")
        if result.failures:
            self.stdout.write(self.style.ERROR(f"销毁失败: {result.failures} 个，下一轮会重试"))

        if skip_archive:
            return

        archived = archive_terminated_sandboxes(dry_run=dry_run)
        retention = settings.AGENT_SANDBOX_E2B_TERMINATED_RETENTION_DAYS
        self.stdout.write(f"过期记录归档: {archived} 条（保留期 {retention} 天）")
