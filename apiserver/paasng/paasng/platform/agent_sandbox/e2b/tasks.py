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

"""e2b 沙箱的异步任务。

对账要逐个集群拉网关清单、再逐个销毁孤儿实例，比平台其余的周期任务重得多，
因此放在 celery worker 里执行，而不是留在同时跑着调度器的 web 进程里：
web 进程会被 gunicorn 的 max-requests 回收，也会随滚动发布随时退出，
而销毁孤儿是有副作用的操作，从中间被截断会留下"一半清理干净、一半没动"的状态。
celery worker 退出前会等当前任务跑完，不会这样截断。
"""

import logging

from celery import shared_task
from django.conf import settings

from paasng.utils.lock import redis_lock

from .reconcile import archive_terminated_sandboxes, reconcile_all

logger = logging.getLogger(__name__)

RECONCILE_LOCK_KEY = "lock:reconcile_e2b_sandboxes"

# 锁的存活时间在任务执行上限之上留出的余量。锁必须活得比任务久，否则它会在任务
# 还在跑的时候过期；余量留给超时后的收尾
RECONCILE_LOCK_TTL_MARGIN_SECONDS = 60


@shared_task(soft_time_limit=settings.AGENT_SANDBOX_E2B_RECONCILE_TIME_LIMIT_SECONDS)
def reconcile_e2b_sandboxes_task():
    """收敛 e2b 沙箱归属表与底层网关的状态差异"""
    timeout = settings.AGENT_SANDBOX_E2B_RECONCILE_TIME_LIMIT_SECONDS + RECONCILE_LOCK_TTL_MARGIN_SECONDS
    # 避免与上一轮尚未结束的对账重叠
    with redis_lock(RECONCILE_LOCK_KEY, timeout=timeout) as acquired:
        if not acquired:
            logger.warning("Another worker is reconciling e2b sandboxes, skip.")
            return

        logger.info("e2b reconcile started")
        result = reconcile_all()
        logger.info(
            "e2b reconcile done: converged=%d orphans_killed=%d orphans_waiting=%d "
            "clusters_done=%d clusters_skipped=%d failures=%d",
            result.converged,
            result.orphans_killed,
            result.orphans_waiting,
            result.clusters_done,
            result.clusters_skipped,
            result.failures,
        )

        # 归档跟着对账一起跑。它只删本地行、不碰网关，放同一轮省一个调度项，
        # 多跑几次也没有副作用
        archive_terminated_sandboxes()
