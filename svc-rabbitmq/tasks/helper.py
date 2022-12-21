# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from datetime import timedelta

from . import models
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


class CallableWrapper:
    def __init__(self, obj: 'callable', *args, **kwargs):
        self._obj = obj
        self._args = args
        self._kwargs = kwargs

    def _wrap(self):
        return self._obj(*self._args, **self._kwargs)

    def __call__(self, *args, **kwargs):
        return self._wrap


class Task:
    def __init__(self, name: 'str', interval: 'int' = 0, enabled: 'bool' = True):
        self._name = name
        self._interval = timedelta(minutes=interval)
        self._enabled = enabled
        self._registered = False

    @classmethod
    def apply(cls, *args, **kwargs):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.apply(*args, **kwargs)

    @classmethod
    def apply_async(cls, *args, **kwargs):
        scheduler = Scheduler.get()
        return scheduler.call(cls.apply, *args, **kwargs)

    @property
    def cron_task(self) -> 'models.CronTask':
        return models.CronTask.objects.get(name=self._name)

    def get_cron_result(self):
        try:
            task = self.cron_task
        except models.CronTask.DoesNotExist:
            return None

        return task.result

    def register_cron_task(self, *args, **kwargs) -> 'models.CronTask':
        if self._registered:
            raise RuntimeError("task has been registered")

        self._registered = True
        return models.CronTask.objects.update_or_create(
            name=self._name,
            defaults={
                "interval": self._interval,
                "enabled": self._enabled,
                "callable": CallableWrapper(self.apply, *args, **kwargs),
            },
        )
