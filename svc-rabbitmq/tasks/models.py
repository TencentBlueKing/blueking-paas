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
import logging
import traceback
import typing
from dataclasses import dataclass

from django.core.cache import caches
from django.db import models
from django.db.transaction import atomic
from django.dispatch import Signal
from django.utils.timezone import now as get_now
from picklefield.fields import PickledObjectField

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from datetime import timedelta

    from django.core.cache.backends.locmem import LocMemCache

sig_task_pre_call = Signal()
sig_task_post_call = Signal()


class TaskExecuteException(Exception):
    """Task failed when executing"""


class CronTaskContext:
    def __init__(self, task: 'CronTask'):
        self.task = task
        self.exception: 'Exception' = None
        self.start_at = None
        self.end_at = None

    def __enter__(self):
        self.start_at = get_now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_at = get_now()

        if exc_tb is None:
            return False

        messages = traceback.format_exception(exc_type, exc_val, exc_tb)
        self.exception = TaskExecuteException("".join(messages))
        return True

    def call(self, func) -> 'CronTaskResult':
        result = None
        with self:
            if not callable(func):
                raise TypeError(f"callable object excepted but got {func}")
            result = func()

        return CronTaskResult(
            task=self.task,
            result=result,
            exception=self.exception,
            duration=self.end_at - self.start_at,
        )


@dataclass
class CronTaskResult:
    task: 'CronTask'
    result: 'typing.Any'
    exception: 'Exception'
    duration: 'timedelta'

    def __call__(self, *args, **kwargs):
        if self.exception is not None:
            raise self.exception
        return self.result


@dataclass
class CachedCronTaskResult:
    raw: 'CronTaskResult'
    missing: 'bool' = False
    cache_key: 'str' = None

    cache_name = "default"

    @property
    def cache(self) -> 'LocMemCache':
        return caches[self.cache_name]

    def flush(self):
        interval = self.raw.task.interval
        self.cache.set(self.cache_key, self.raw.result, interval.total_seconds() * 10)
        self.raw.result = None
        self.missing = True

    def __post_init__(self):
        self.cache_key = f"cron_task::result::{self.raw.task.name}"

    def __call__(self, *args, **kwargs):
        if self.missing:
            value = self.cache.get(self.cache_key)
            self.raw.result = value
            self.missing = False

        return self.raw()


def _default_pre_call(task):
    return task.callable


def _default_post_call(result: 'CronTaskResult'):
    cache_result = CachedCronTaskResult(result)
    cache_result.flush()
    return cache_result


class CronTaskManager(models.Manager):
    def prepared_tasks(self) -> 'typing.List[CronTask]':
        tasks = []
        with atomic(self.db):
            for t in self.exclude(next_run_time=None).filter(next_run_time__lte=get_now(), enabled=True):
                t.forward()
                t.save()
                tasks.append(t)
        logger.debug("prepared cron tasks %s", tasks)
        return tasks


class CronTask(models.Model):
    name = models.CharField(max_length=255, unique=True)  # id of task
    interval = models.DurationField()
    next_run_time = models.DateTimeField(db_index=True, blank=True, null=True, default=get_now)
    last_run_time = models.DateTimeField(blank=True, null=True)
    enabled = models.BooleanField(default=False)

    callable = PickledObjectField(default=None, null=False)
    get_result = PickledObjectField(default=None, null=True)
    pre_call = PickledObjectField(default=None, null=True)
    post_call = PickledObjectField(default=None, null=True)

    objects = CronTaskManager()

    class Meta:
        ordering = ('next_run_time', 'name')

    def __str__(self):
        return f"{self.name}[{self.id}]"

    @property
    def result(self):
        if not callable(self.get_result):
            return None
        return self.get_result()

    def apply(self) -> 'CronTaskResult':
        pre_call = self.pre_call or _default_pre_call
        post_call = self.post_call or _default_post_call

        sig_task_pre_call.send(self)
        func = pre_call(self)

        context = CronTaskContext(self)
        result = context.call(func)

        result = post_call(result)
        sig_task_post_call.send(self)

        return result

    def forward(self):
        now = get_now()
        next_run_time = self.next_run_time + self.interval
        if next_run_time <= now:
            self.next_run_time = now

        self.last_run_time = self.next_run_time
        if not self.interval:
            self.next_run_time = None
            return False
        self.next_run_time += self.interval
        return True

    def do(self):
        self.get_result = self.apply()
        self.save(update_fields=["get_result"])
