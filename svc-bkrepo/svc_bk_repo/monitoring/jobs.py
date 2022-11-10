# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import atexit
import errno
import functools
import logging
import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from django.conf import settings
from filelock import FileLock
from paas_service.models import Plan, ServiceInstance
from svc_bk_repo.monitoring.models import RepoQuotaStatistics
from svc_bk_repo.vendor.helper import BKGenericRepoManager

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
        raise ValueError('invalid PID 0')
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


@functools.lru_cache()
def get_repo_manager(plan_id: str):
    plan = Plan.objects.get(pk=plan_id)
    plan_config = plan.get_config()
    manager = BKGenericRepoManager(**plan_config)
    return manager


@scheduler.scheduled_job('interval', minutes=settings.BKREPO_COLLECT_INTERVAL_MINUTES)
def update_bkrepo_quota_statistics():
    """Update bkrepo quota statistics periodically"""
    logger.info("Starting update bkrepo quota.")
    for instance in ServiceInstance.objects.all():
        manager = get_repo_manager(instance.plan_id)

        credentials = instance.get_credentials()
        private_bucket = credentials["private_bucket"]
        public_bucket = credentials["public_bucket"]
        private_quota = manager.get_repo_quota(private_bucket)
        public_quota = manager.get_repo_quota(public_bucket)

        RepoQuotaStatistics.objects.update_or_create(
            instance=instance,
            repo_name=private_bucket,
            defaults={"max_size": private_quota.max_size, "used": private_quota.used},
        )
        RepoQuotaStatistics.objects.update_or_create(
            instance=instance,
            repo_name=public_bucket,
            defaults={"max_size": public_quota.max_size, "used": public_quota.used},
        )
    logger.info("bkrepo quota updated.")
