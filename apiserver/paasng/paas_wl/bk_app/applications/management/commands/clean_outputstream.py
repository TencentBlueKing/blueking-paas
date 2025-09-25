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

import logging
import time
from datetime import datetime
from typing import Iterator, List

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from paas_wl.bk_app.applications.models.misc import OutputStream, OutputStreamLine

logger = logging.getLogger(__name__)


OBSOLETE_MESSAGE = (
    "This deployment log is unavailable, it was removed according to the platform's log retention policy."
)


class Command(BaseCommand):
    """清理过期的 OutputStream 记录的详情记录数据

    对于 2 年前的部署日志数据进行"压缩"处理：
    1. 删除所有日志记录
    2. 插入一条提示信息, 告知日志已被平台按照保留策略删除
    """

    # 限流参数, 每执行 1000 条记录休眠 1 秒
    throttle_count = 1000
    throttle_sleep = 1

    def add_arguments(self, parser):
        parser.add_argument(
            "--before_months",
            type=int,
            default=12 * 2,
            help="删除多少个月之前的 OutputStream 记录，默认值为 12 * 2 (2 年)",
        )
        parser.add_argument(
            "--dry_run",
            action="store_true",
            help="预览模式，不执行实际删除操作",
        )
        parser.add_argument("--batch_size", type=int, default=500, help="分批处理大小, 默认 500")

    def handle(self, *args, **options):
        before_months = options["before_months"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        cutoff_date = timezone.now() - relativedelta(months=before_months)

        self.stdout.write(
            self.style.SUCCESS(
                f"开始清理 {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} 之前的 OutputStream 详细数据记录"
            )
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("运行在预览模式，不会执行实际删除操作"))

        processed_count = 0
        compressed_count = 0
        since_last_throttle = 0

        # 批量处理压缩任务
        worker = self._preview_uuid_batch if dry_run else self._compress_uuid_batch
        for batch_streams in self._get_streams_in_batches(cutoff_date, batch_size):
            compressed_count += worker(batch_streams)
            processed_count += len(batch_streams)
            since_last_throttle += len(batch_streams)
            self.stdout.write(f"已处理 {processed_count} 个 OutputStream 记录")

            # 限流
            if (not dry_run) and since_last_throttle >= self.throttle_count:
                self.stdout.write(f"休眠 {self.throttle_sleep} 秒，防止数据库压力过大")
                time.sleep(self.throttle_sleep)
                since_last_throttle = 0

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[预览完成] 共处理 {processed_count} 个 OutputStream，可压缩 {compressed_count} 个记录"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[处理完成] 共处理 {processed_count} 个 OutputStream，实际压缩 {compressed_count} 个记录"
                )
            )

    def _get_streams_in_batches(self, cutoff_date: datetime, batch_size: int) -> Iterator[List[str]]:
        """获取过期的 OutputStream 记录，按批次返回"""
        uuid_qs = (
            OutputStream.objects.filter(created__lt=cutoff_date)
            .values_list("uuid", flat=True)
            .iterator(chunk_size=1000)
        )

        current_ids: List[str] = []
        for uuid in uuid_qs:
            current_ids.append(uuid)
            if len(current_ids) >= batch_size:
                yield current_ids
                current_ids = []

        if current_ids:
            yield current_ids

    def _preview_uuid_batch(self, stream_ids: List[str]) -> int:
        """预览模式"""

        compressed_count = 0

        for stream_id in stream_ids:
            count = OutputStreamLine.objects.filter(output_stream_id=stream_id).count()
            if count <= 1:
                self.stdout.write(f"[预览] OutputStream {stream_id}: 只有 {count} 条详细记录, 无需压缩")
            else:
                self.stdout.write(f"[预览] OutputStream {stream_id}: 将删除 {count} 条详细记录, 添加 1 条提示信息")
                compressed_count += 1

        return compressed_count

    def _compress_uuid_batch(self, stream_ids: List[str]) -> int:
        """批量压缩 OutputStream 记录"""
        compressed_count = 0
        for stream_id in stream_ids:
            try:
                queryset = OutputStreamLine.objects.filter(output_stream_id=stream_id).order_by("-created")
                count = queryset.count()
                if count <= 1:
                    logger.debug(f"OutputStream {stream_id} 详细记录只有 {count} 条，跳过, 无需压缩")
                    continue

                recycle_time = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
                # 最后一条记录的时间
                last_line_created = timezone.localtime(queryset.first().created).strftime("%Y-%m-%d %H:%M:%S")
                # 单个 OutputStream 单独事务
                with transaction.atomic():
                    deleted_count, _ = OutputStreamLine.objects.filter(output_stream_id=stream_id).delete()

                    info_message = (
                        f"{OBSOLETE_MESSAGE}\n[Original log info] line count: {deleted_count},"
                        f" created at: {last_line_created}, removed at: {recycle_time}\n\n"
                    )

                    OutputStreamLine.objects.create(
                        output_stream_id=stream_id,
                        line=info_message,
                        stream="STDOUT",
                    )
                    logger.info(f"成功压缩 OutputStream {stream_id}，删除了 {deleted_count} 条详细记录")
                    compressed_count += 1
            except Exception:
                logger.exception(f"压缩 OutputStream {stream_id} 失败")

        return compressed_count
