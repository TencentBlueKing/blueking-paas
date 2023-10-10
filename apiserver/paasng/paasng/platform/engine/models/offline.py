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

from django.db import models
from django.utils import timezone

from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations

from .base import OperationVersionBase

logger = logging.getLogger(__name__)


class OfflineOperationQuerySet(models.QuerySet):
    def latest_succeeded(self):
        """Return the latest succeeded deployment of queryset"""
        return self.filter(status=JobStatus.SUCCESSFUL.value).latest('created')

    def get_latest_resumable(self, max_resumable_seconds: int) -> 'OfflineOperation':
        """return the latest resumable offline_operation queryset"""
        offline_operation = self.latest('created')
        if (
            offline_operation.status == JobStatus.PENDING.value
            and (timezone.now() - offline_operation.created).total_seconds() <= max_resumable_seconds
        ):
            return offline_operation
        raise OfflineOperation.DoesNotExist("the latest offline operation is not resumable")


class OfflineOperation(OperationVersionBase):
    """部署记录"""

    app_environment = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, related_name='offlines', null=True
    )

    status = models.CharField(u"下线状态", choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value)

    log = models.TextField(u"下线日志", null=True, blank=True)
    err_detail = models.TextField(u"下线异常原因", null=True, blank=True)

    objects = OfflineOperationQuerySet().as_manager()

    def __str__(self):
        return "{app}-{env}-{status}".format(
            app=self.app_environment.application.name, env=self.app_environment.environment, status=self.status
        )

    def set_log(self, content=''):
        self.log = content
        self.save(update_fields=['log'])

    def append_log(self, content=''):
        if self.log is None:
            self.log = content
        else:
            self.log += content + '\n'
        self.save(update_fields=['log'])

    def update_operation_status(self, status):
        """Update related operation status"""
        ModuleEnvironmentOperations.objects.filter(object_uid=self.pk).update(status=status)

    def has_succeeded(self):
        return self.status == JobStatus.SUCCESSFUL.value

    def set_failed(self, message: str):
        """Set current operation as failed

        :param message: error detail message
        """
        self.append_log(message)
        self.status = JobStatus.FAILED.value
        self.err_detail = message
        self.save(update_fields=['status', 'err_detail'])

        # Update related Module operation object
        self.update_operation_status(JobStatus.FAILED.value)

    def set_successful(self):
        """Set current operation as successful"""
        self.append_log('offline succeeded.')
        self.status = JobStatus.SUCCESSFUL.value
        self.save(update_fields=['status'])

        # Update related Module operation object
        self.update_operation_status(JobStatus.SUCCESSFUL.value)
        # Update related app environment
        if self.app_environment.is_offlined is False:
            self.app_environment.is_offlined = True
            self.app_environment.save(update_fields=['is_offlined'])
