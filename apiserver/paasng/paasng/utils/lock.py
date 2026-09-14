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

"""基于 Redis 的跨进程协调原语。

平台的 web、celery worker 都是多副本，进程内的锁没有意义，需要落到共享存储上。
"""

import logging
from contextlib import contextmanager

from paasng.core.core.storages.redisdb import get_default_redis

logger = logging.getLogger(__name__)


@contextmanager
def redis_lock(lock_key: str, timeout: int = 300):
    """Redis 分布式锁上下文管理器，确保跨进程的原子操作

    注意 timeout 只是防死锁的兜底，不构成"执行期间必然持有锁"的保证：调用方跑得
    比 timeout 久时锁会提前过期，此时互斥已经失效。timeout 要按最坏执行时间来给。

    :param lock_key: 锁的唯一标识键，建议遵循命名规范如 lock:<业务场景>
    :param timeout: 锁自动释放的超时时间（秒），预防死锁
    """
    redis_conn = get_default_redis()
    lock = redis_conn.lock(
        name=lock_key,
        timeout=timeout,
        blocking_timeout=0,  # 非阻塞模式，立即返回
        thread_local=False,
    )

    acquired = lock.acquire()
    try:
        if acquired:
            logger.debug("Successfully acquired lock for %s", lock_key)
        else:
            logger.debug("Failed to acquire lock for %s", lock_key)
        yield acquired
    finally:
        # 只有当前进程持有的锁才释放
        if acquired:
            lock.release()
            logger.debug("Released lock for %s", lock_key)


def acquire_once_per_period(key: str, period: int) -> bool:
    """在一个周期内只放行一次调用。

    与 `redis_lock` 的区别是拿到之后不归还，键只靠 TTL 过期，因此"一个周期一次"
    与调用方执行多久无关。适合把多个副本各自触发的周期性动作收敛成一次。

    :param key: 标识该周期性动作的唯一键，建议遵循命名规范如 periodic:<业务场景>
    :param period: 周期长度（秒），也就是键的存活时间
    :return: 本周期内是否轮到调用方执行
    """
    redis_conn = get_default_redis()
    # SET NX EX 是单条命令，多个副本同时到点也只有一个能写入成功
    return bool(redis_conn.set(key, b"1", nx=True, ex=period))
