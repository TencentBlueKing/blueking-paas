# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import uuid

from django.db import models

from paasng.platform.engine.constants import JobStatus, OperationTypes
from paasng.utils.models import BkUserField, TimestampedModel


class OperationQuerySet(models.QuerySet):
    """Custom QuerySet for ModuleEnvironmentOperations model"""

    def owned_by_module(self, module, environment=None):
        """Return deployments owned by module"""
        envs = module.envs.all()
        if environment:
            envs = [
                envs.get(environment=environment),
            ]
        return self.filter(app_environment__in=envs)


class ModuleEnvironmentOperations(TimestampedModel):
    """
    [multi-tenancy] TODO
    """

    id = models.UUIDField("UUID", default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="module_operations"
    )
    app_environment = models.ForeignKey(
        "applications.ApplicationEnvironment", on_delete=models.CASCADE, related_name="module_operations", null=True
    )
    operator = BkUserField()
    operation_type = models.CharField(max_length=32, choices=OperationTypes.get_choices())
    object_uid = models.UUIDField("详情记录的UUID", default=uuid.uuid4, editable=False)
    status = models.CharField(
        "操作状态", choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value
    )

    objects = OperationQuerySet().as_manager()

    def __str__(self):
        return "{app_name}-{env}-{operation_type}-{operator}".format(
            app_name=self.application.code,
            env=self.app_environment.environment,
            operation_type=self.operation_type,
            operator=self.operator,
        )

    def get_detail(self):
        if self.operation_type == OperationTypes.ONLINE.value:
            from .deployment import Deployment

            obj = Deployment.objects.get(pk=self.object_uid)
        else:
            from .offline import OfflineOperation

            obj = OfflineOperation.objects.get(pk=self.object_uid)
        return obj

    def get_offline_obj(self):
        return self.get_detail() if self.operation_type == OperationTypes.OFFLINE.value else None

    def get_deployment_obj(self):
        return self.get_detail() if self.operation_type == OperationTypes.ONLINE.value else None
