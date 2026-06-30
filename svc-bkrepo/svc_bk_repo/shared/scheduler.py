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
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
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
