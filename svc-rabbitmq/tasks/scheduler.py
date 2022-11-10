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
import logging
import os
import signal
import threading
import typing
from multiprocessing import pool
from uuid import uuid4

from django import db as django_db
from django.conf import settings

from .models import CronTask, sig_task_post_call, sig_task_pre_call

if typing.TYPE_CHECKING:
    import queue

logger = logging.getLogger(__name__)


def _global_process_pool_creator() -> 'pool.Pool':
    return pool.Pool(
        processes=settings.MAX_TASK_WORKERS,
        maxtasksperchild=settings.MAX_TASK_PRE_WORKER,
        initializer=_sub_process_poll_initializer,
    )


def _sub_process_poll_initializer():
    sig_task_pre_call.connect(django_db.close_old_connections)
    sig_task_post_call.connect(django_db.close_old_connections)
    start_threading_scheduler()


def process_pool_creator() -> 'pool.Pool':
    return pool.Pool(processes=settings.MAX_TASK_WORKERS, maxtasksperchild=settings.MAX_TASK_PRE_WORKER)


def threading_pool_creator() -> 'pool.ThreadPool':
    return pool.ThreadPool(processes=settings.MAX_TASK_WORKERS)


def start_threading_scheduler():
    scheduler = Scheduler.init(threading_pool_creator, False)
    scheduler.start()


class SchedulerMonitor(threading.Thread):
    def __init__(self, scheduler: 'Scheduler', done: 'threading.Condition', cron_interval: 'int'):
        self._scheduler = scheduler
        self._done = done
        self._cron_interval = cron_interval
        self._cron_triggered = 0
        super().__init__(daemon=True)

    def _wait_done_signal(self):
        with self._done:
            return self._done.wait(self._cron_interval)

    def stats(self) -> 'typing.Dict':
        return {
            "cron_triggered": self._cron_triggered,
        }

    def handle_cron_tasks(self):
        django_db.close_old_connections()
        tasks = CronTask.objects.prepared_tasks()
        logger.info("scheduler %s ready to handle %d cron tasks", self._scheduler.uuid, len(tasks))
        for t in tasks:
            self._scheduler.call(t.do)

        self._cron_triggered = self._cron_triggered + 1

    def run(self):
        try:
            while not self._wait_done_signal():
                self.handle_cron_tasks()
        except Exception:
            logger.exception("scheduler monitor crash, dying")
            self._scheduler.stop()
            os.kill(os.getpid(), signal.SIGTERM)


class Scheduler:
    _global = None

    @classmethod
    def stop_global(cls):
        if cls._global:
            cls._global.stop()

    @classmethod
    def get(cls) -> 'Scheduler':
        if cls._global is None:
            raise RuntimeError("scheduler not ready")
        return cls._global

    @classmethod
    def init(cls, *args, **kwargs):
        cls._global = cls(*args, **kwargs)
        return cls._global

    def __init__(self, pool_creator, is_master=False):
        self.uuid = uuid4().hex
        self._done = threading.Condition()
        self._pool_creator = pool_creator
        self._pool: 'pool.Pool' = None
        self._is_master = is_master
        self._monitor = SchedulerMonitor(self, self._done, settings.CRON_TASK_CHECK_INTERVAL)

    @property
    def pid(self):
        return os.getpid()

    def stats(self) -> 'typing.Dict':
        stats = self._monitor.stats()
        task_queue: 'queue.Queue' = self._pool._taskqueue
        stats.update(
            {
                "tasks": task_queue.qsize(),
            }
        )
        return stats

    def call(self, func, *args, **kwargs):
        return self._pool.apply_async(func, args, kwargs)

    def start(self):
        self._pool = self._pool_creator()
        if self._is_master:
            self._monitor.start()
        logger.info(
            "scheduler %s:%s started, process pool: %s, master: %s", self.uuid, self.pid, self._pool, self._is_master
        )

    def stop(self):
        with self._done:
            self._done.notify_all()
        if self._pool:
            self._pool.close()
            self._pool.join()


def ready():
    if not settings.SCHEDULER_ENABLED:
        return

    scheduler = Scheduler.init(_global_process_pool_creator, True)
    scheduler.start()
    atexit.register(scheduler.stop)
