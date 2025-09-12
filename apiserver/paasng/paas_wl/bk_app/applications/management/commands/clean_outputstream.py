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
from datetime import datetime, timedelta
from typing import Iterator, List

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Max, Min
from django.utils import timezone

from paas_wl.bk_app.applications.models.misc import OutputStream, OutputStreamLine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """清理过期的 OutputStream 记录的详情记录数据

    对于 2 年前的部署日志数据进行"压缩"处理：
    1. 保留第一条日志记录
    2. 删除其余所有日志记录
    3. 插入一条提示信息："The remaining deployment log content is obsolete and cannot be viewed !"
    """

    help = "压缩过期的 OutputStream 记录，默认保留最近两年的记录：保留第一条日志，删除其余并插入提示信息"
    OBSOLETE_MESSAGE = "The remaining deployment log content is obsolete and cannot be viewed !"

    def add_arguments(self, parser):
        parser.add_argument(
            "--before-days",
            type=int,
            default=365 * 2,
            help="删除多少天之前的 OutputStream 记录，默认值为 365 * 2 (2 年)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="预览模式，不执行实际删除操作",
        )
        parser.add_argument("--batch-size", type=int, default=500, help="分批处理大小, 默认 500")

    def handle(self, *args, **options):
        before_days = options["before_days"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        cutoff_date = timezone.now() - timedelta(days=before_days)

        self.stdout.write(
            self.style.SUCCESS(f"开始清理 {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} 之前的 OutputStream 数据")
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("运行在预览模式，不会执行实际删除操作"))

        processed_count = 0
        compressed_count = 0

        # 批量处理压缩任务
        for batch_streams in self._get_streams_in_batches(cutoff_date, batch_size):
            if dry_run:
                compressed_count += self._preview_batch(batch_streams)
                processed_count += len(batch_streams)
            else:
                compressed_count += self._compress_streams_batch(batch_streams)
                processed_count += len(batch_streams)
                self.stdout.write(f"已处理 {processed_count} 个记录")

        self.stdout.write(
            self.style.SUCCESS(
                f"处理完成！共处理 {processed_count} 个 OutputStream ，实际压缩 {compressed_count} 个记录"
            )
        )

    def _get_streams_in_batches(self, cutoff_date: datetime, batch_size: int) -> Iterator[List[OutputStream]]:
        """获取需要压缩的 OutputStream 记录，按批次返回"""
        time_range = OutputStream.objects.filter(created__lt=cutoff_date).aggregate(
            min_time=Min("created"), max_time=Max("created")
        )
        if not time_range["min_time"]:
            return

        # 计算时间分片
        start_time: datetime = time_range["min_time"]
        end_time: datetime = time_range["max_time"]
        total_seconds = (end_time - start_time).total_seconds()
        time_step = timedelta(seconds=max(total_seconds / 100, 3600))  # 最少1小时间隔

        current_batch: List[OutputStream] = []
        current_time = start_time

        while current_time < end_time:
            next_time = min(current_time + time_step, end_time)

            # 获取当前时间端的可压缩记录
            compressible_streams = self._get_compressible_streams_in_range_time(current_time, next_time)

            for stream in compressible_streams:
                current_batch.append(stream)
                if len(current_batch) >= batch_size:
                    yield current_batch
                    current_batch = []

            current_time = next_time

        if current_batch:
            yield current_batch

    def _get_compressible_streams_in_range_time(self, start_time: datetime, end_time: datetime) -> List[OutputStream]:
        """获取指定时间范围内可以被压缩的记录"""
        expired_streams = list(
            OutputStream.objects.filter(created__gte=start_time, created__lte=end_time).order_by("created")
        )

        if not expired_streams:
            return []

        stream_uuids = [stream.uuid for stream in expired_streams]

        # 查找已经被压缩的过期记录
        compressed_ids = set(
            OutputStreamLine.objects.filter(output_stream_id__in=stream_uuids, stream="SYSTEM").values_list(
                "output_stream_id", flat=True
            )
        )

        # 查找有多条日志行的过期记录
        multi_line_ids = set(
            OutputStreamLine.objects.filter(output_stream_id__in=stream_uuids)
            .values("output_stream_id")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .values_list("output_stream_id", flat=True)
        )

        compressible_ids = multi_line_ids - compressed_ids

        return [stream for stream in expired_streams if stream.uuid in compressible_ids]

    def _preview_batch(self, streams: List[OutputStream]) -> int:
        """预览模式: 统计可以被压缩的 OutputStream 记录数"""
        compressed_count = 0
        for stream in streams:
            line_count = OutputStreamLine.objects.filter(output_stream=stream).count()
            if line_count > 1:
                self.stdout.write(
                    f"[预览] OutputStream {stream.uuid}: 将保留第一条记录，删除其余 {line_count - 1} 条记录"
                )
                compressed_count += 1
        return compressed_count

    def _compress_streams_batch(self, streams: List[OutputStream]) -> int:
        """批量压缩 OutputStream 记录"""
        compressed_count = 0
        for stream in streams:
            try:
                with transaction.atomic():
                    if self._compress_single_stream(stream):
                        compressed_count += 1
            except Exception:
                logger.exception(f"压缩 OutputStream {stream.uuid} 失败")

        return compressed_count

    def _compress_single_stream(self, stream: OutputStream) -> bool:
        """压缩单个 OutputStream"""
        # 获取第一条记录
        first_line = OutputStreamLine.objects.filter(output_stream=stream).order_by("created").first()

        if not first_line:
            logger.warning(f"OutputStream {stream.uuid} 没有任何日志行，跳过压缩")
            return False

        # 删除除第一条之外的所有记录
        deleted_count = OutputStreamLine.objects.filter(output_stream=stream).exclude(id=first_line.id).delete()[0]

        if deleted_count > 0:
            # 插入压缩提示信息
            OutputStreamLine.objects.create(output_stream=stream, line=self.OBSOLETE_MESSAGE, stream="SYSTEM")
            logger.info(f"成功压缩 OutputStream {stream.uuid}，删除了 {deleted_count} 条详细记录")
            return True

        return False
