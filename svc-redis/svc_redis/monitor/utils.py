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

"""采集的并发与超时控制"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Callable

from django.conf import settings

logger = logging.getLogger(__name__)

# 并发采集的最大并发数
MAX_CONCURRENT_TASKS = 32


def collect_deadline() -> float:
    """本次采集的截止时间 (time.monotonic() 时间戳)"""
    return time.monotonic() + settings.METRIC_COLLECT_DEADLINE


def remaining_time(deadline: float) -> float:
    """距离 deadline 还剩多少秒 (可能为负)"""
    return deadline - time.monotonic()


def map_concurrently(func: Callable, items: list, deadline: float) -> list:
    """并发执行任务并收集结果, 到 deadline 仍未完成的任务被放弃

    NOTE: 被放弃的任务仍会继续跑完, 因此 func 必须是纯函数, 不得修改传入对象或其它共享状态.
    """
    if not items:
        return []

    timeout = remaining_time(deadline)
    if timeout <= 0:
        logger.warning("collecting metrics deadline exceeded, skip %d task(s)", len(items))
        return []

    executor = ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_TASKS, len(items)))
    try:
        futures = [executor.submit(func, item) for item in items]
        done, not_done = wait(futures, timeout=timeout)
        if not_done:
            logger.warning("collecting metrics timeout, %d/%d unfinished task(s) skipped", len(not_done), len(futures))
    finally:
        # 不等待未完成的任务, 避免拖慢采集; 它们不会再修改共享对象
        executor.shutdown(wait=False, cancel_futures=True)

    results = []
    for future in done:
        try:
            results.append(future.result())
        except Exception:
            # 单个任务失败不得影响整次采集
            logger.exception("unexpected error in concurrent collect task")
    return results
