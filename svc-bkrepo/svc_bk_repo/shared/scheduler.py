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

import atexit
import errno
import logging
import os
from contextlib import contextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from django.db import connection
from filelock import FileLock

logger = logging.getLogger(__name__)
scheduler = Scheduler()

SCHEDULER_LOCK_FILE = "scheduler.lock"
SCHEDULER_PID_FILE = "scheduler.pid"


def process_exists(pid: int):
    """Check whether pid exists in the current process table. UNIX only."""
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError("invalid PID 0")
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True


def start_scheduler():
    lock = FileLock(lock_file=SCHEDULER_LOCK_FILE)
    with lock:
        pid = Path(SCHEDULER_PID_FILE)
        if pid.exists() and process_exists(int(pid.read_text())):
            logger.info("Scheduler should be running")
            return

        pid.write_text(str(os.getpid()))
    logger.info("Start scheduler!")
    scheduler.start()
    atexit.register(clear_lock)


def clear_lock():
    logger.info("clear scheduler.pid")
    pid = Path(SCHEDULER_PID_FILE)
    pid.unlink()


@contextmanager
def db_distributed_lock(lock_name: str):
    """基于 MySQL GET_LOCK 的分布式锁, 确保多副本部署时同一 job 只被一个 Pod 执行.

    用法:
        with db_distributed_lock("auto_extend_bkrepo_quota") as acquired:
            if not acquired:
                return
            实际逻辑...

    原理:
        MySQL GET_LOCK(name, timeout) 是会话级命名锁, 原子操作.
        - timeout=0: 非阻塞, 拿不到立即返回 0
        - 连接断开时 MySQL 自动释放, 天然崩溃安全

    Args:
        lock_name: 锁名称, 同一任务使用相同名称
    """
    acquired = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 0)", [lock_name])
            acquired = bool(cursor.fetchone()[0])
        if acquired:
            logger.info("Distributed lock '%s' acquired.", lock_name)
        else:
            logger.info("Distributed lock '%s' is held by another instance, skip.", lock_name)
        yield acquired
    except Exception:
        logger.exception("Error while acquiring distributed lock '%s'", lock_name)
        yield False
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT RELEASE_LOCK(%s)", [lock_name])
            logger.info("Distributed lock '%s' released.", lock_name)
