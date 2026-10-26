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

"""回收长期没人用的发布源码包。

适合由定时任务周期执行，例如每天一次::

    python manage.py delete_unused_source_packages             # 删除 15 天未被使用的包
    python manage.py delete_unused_source_packages --days 30
    python manage.py delete_unused_source_packages --dry-run   # 只列出，不删除
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from app_spark_api.repository.git.source_packages import (
    DEFAULT_UNUSED_FOR,
    MAX_URL_EXPIRES_IN,
    delete_unused_source_packages,
)


class Command(BaseCommand):
    help = "删除超过指定天数未被使用（上传、复用或签下载地址）的发布源码包，包括记录和制品库中的对象。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_UNUSED_FOR.days,
            help=(
                f"未被使用超过多少天的包会被删除，默认 {DEFAULT_UNUSED_FOR.days}。"
                f"必须大于预签名地址的最长有效期（{MAX_URL_EXPIRES_IN // 86400} 天），"
                "否则已签出的地址可能在过期前就指向一个被删掉的包。"
            ),
        )
        parser.add_argument("--dry-run", action="store_true", help="只列出将被删除的包，不做任何删除。")

    def handle(self, *args: Any, days: int, dry_run: bool, **options: Any) -> None:
        try:
            reclaimed = delete_unused_source_packages(timedelta(days=days), dry_run=dry_run)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        verb = "Would delete" if dry_run else "Deleted"
        for package in reclaimed.packages:
            self.stdout.write(
                f"{verb} {package.project_id}@{package.commit_sha} "
                f"(last used {package.last_used_at.isoformat()}): {package.bucket}/{package.key}"
            )
        self.stdout.write(f"{verb} {len(reclaimed.packages)} source package(s) unused for {days} day(s).")

        # 记录已经删掉、对象没删成：它们只占空间，但要让定时任务以失败告终，好有人去手工清理。
        if reclaimed.orphaned_keys:
            keys = ", ".join(reclaimed.orphaned_keys)
            raise CommandError(f"Could not delete {len(reclaimed.orphaned_keys)} blob(s) from BkRepo: {keys}")
