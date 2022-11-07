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

from bkpaas_auth import get_user_by_user_id
from django.db import models
from jsonfield import JSONField

from paasng.engine.constants import JobStatus
from paasng.engine.models.base import OperationVersionBase
from paasng.engine.models.deployment import Deployment
from paasng.utils.models import TimestampedModel

from .base import AtomData
from .constants import CIBackend

logger = logging.getLogger(__name__)


class CIResourceAppEnvRelation(TimestampedModel):
    """CI 资源"""

    credentials = JSONField(default={})
    env = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, related_name='ci_resources', null=True
    )
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    backend = models.CharField(verbose_name="CI引擎", choices=CIBackend.get_django_choices(), max_length=32)

    class Meta:
        get_latest_by = 'created'


class CIResourceAtom(TimestampedModel):
    """CI 资源原子"""

    id = models.CharField("原子 ID", max_length=64, unique=True, db_index=True, primary_key=True)
    name = models.CharField("原子名称", max_length=32)
    env = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, related_name='ci_resource_atoms', null=True
    )
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    resource = models.ForeignKey(CIResourceAppEnvRelation, on_delete=models.CASCADE, related_name="related_atoms")
    backend = models.CharField(verbose_name="CI引擎", choices=CIBackend.get_django_choices(), max_length=32)

    class Meta:
        unique_together = ('env', 'name', 'backend')

    def to_simple_data(self):
        return AtomData(name=self.name, id=self.id)


class CIAtomJob(OperationVersionBase):
    """CI 任务执行情况"""

    status = models.CharField(
        verbose_name="执行状态", choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value
    )
    backend = models.CharField(verbose_name="CI引擎", choices=CIBackend.get_django_choices(), max_length=32)
    env = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, related_name='ci_atom_jobs', null=True
    )
    deployment = models.OneToOneField(Deployment, on_delete=models.CASCADE, related_name='ci_job', null=True)
    atom = models.ForeignKey(CIResourceAtom, on_delete=models.CASCADE, related_name="related_jobs")
    build_id = models.CharField(verbose_name="构建ID", max_length=128)
    output = JSONField(default={})

    def finish(self, status: JobStatus):
        self.status = status
        self.save(update_fields=['status'])

    def to_dict(self):
        return dict(
            backend=self.backend,
            operator=get_user_by_user_id(self.operator).username,
            build_id=self.build_id,
            atom_id=self.atom.id,
            credentials=self.atom.resource.credentials,
        )
