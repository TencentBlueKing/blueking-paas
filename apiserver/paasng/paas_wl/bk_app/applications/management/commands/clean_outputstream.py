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
from datetime import datetime
from typing import Dict, Iterator, List

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from paas_wl.bk_app.applications.models.misc import OutputStream, OutputStreamLine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """清理过期的 OutputStream 记录的详情记录数据

    对于 2 年前的部署日志数据进行"压缩"处理：
    1. 删除所有日志记录
    2. 插入一条提示信息："The deployment log content is obsolete and cannot be viewed !"
    """

    help = "压缩过期的 OutputStream 记录，默认保留最近两年的记录：删除详细记录并插入提示信息"
    OBSOLETE_MESSAGE = "The deployment log content is obsolete and cannot be viewed !"

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

        # 批量处理压缩任务
        worker = self._preview_batch if dry_run else self._compress_streams_batch
        for batch_streams in self._get_streams_in_batches(cutoff_date, batch_size):
            compressed_count += worker(batch_streams)
            processed_count += len(batch_streams)
            self.stdout.write(f"已处理 {processed_count} 个 OutputStream 记录")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"预览完成！共 {compressed_count} 个 OutputStream 记录可以被压缩"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"处理完成！共处理 {processed_count} 个 OutputStream ，实际压缩 {compressed_count} 个记录"
                )
            )

    def _get_streams_in_batches(self, cutoff_date: datetime, batch_size: int) -> Iterator[List[OutputStream]]:
        """获取需要压缩的 OutputStream 记录，按批次返回"""
        uuid_qs = (
            OutputStream.objects.filter(created__lt=cutoff_date)
            .annotate(lines_count=Count("lines"))
            .filter(lines_count__gt=1)
            .values_list("uuid", flat=True)
            .iterator(chunk_size=1000)
        )

        current_ids: List[str] = []
        for uuid in uuid_qs:
            current_ids.append(uuid)
            if len(current_ids) >= batch_size:
                yield list(OutputStream.objects.filter(uuid__in=current_ids))
                current_ids = []

        if current_ids:
            yield list(OutputStream.objects.filter(uuid__in=current_ids))

    def _preview_batch(self, streams: List[OutputStream]) -> int:
        """预览模式: 统计可以被压缩的 OutputStream 记录数"""
        if not streams:
            return 0

        compressed_count = 0
        stream_ids = [stream.uuid for stream in streams]
        line_counts: Dict[str, int] = dict(
            OutputStreamLine.objects.filter(output_stream_id__in=stream_ids)
            .values("output_stream_id")
            .annotate(count=Count("id"))
            .values_list("output_stream_id", "count")
        )

        for stream in streams:
            line_count = line_counts[stream.uuid]
            if line_count > 1:
                self.stdout.write(f"[预览] OutputStream {stream.uuid}: 将删除 {line_count} 条记录, 添加 1 条提示信息")
                compressed_count += 1
        return compressed_count

    def _compress_streams_batch(self, streams: List[OutputStream]) -> int:
        """批量压缩 OutputStream 记录"""
        if not streams:
            return 0

        stream_ids = [stream.uuid for stream in streams]
        compressed_count = 0
        try:
            with transaction.atomic():
                deleted_count, _ = OutputStreamLine.objects.filter(output_stream_id__in=stream_ids).delete()
                logger.info(f"删除了 {deleted_count} 条 OutputStreamLine 记录")

                if deleted_count == 0:
                    return 0

                now = timezone.now()
                objs = [
                    OutputStreamLine(
                        output_stream_id=sid,
                        line=self.OBSOLETE_MESSAGE,
                        stream="SYSTEM",
                        created=now,
                        updated=now,
                    )
                    for sid in stream_ids
                ]
                OutputStreamLine.objects.bulk_create(objs)

                compressed_count = len(objs)
                logger.info(f"成功压缩 {compressed_count} 条 OutputStream，删除了 {deleted_count} 条详细记录")
        except Exception:
            logger.exception("批量压缩 OutputStream 失败")

        return compressed_count
