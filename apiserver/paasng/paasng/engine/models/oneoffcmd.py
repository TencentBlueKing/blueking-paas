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
import uuid

from django.db import models

from paasng.utils.models import BkUserField, TimestampedModel

from ..constants import JobStatus


class OneOffCommand(TimestampedModel):
    id = models.UUIDField('UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    deployment = models.ForeignKey(
        'engine.Deployment', on_delete=models.CASCADE, related_name='oneoffcommands', null=True
    )
    engine_cmd_id = models.UUIDField('engine command id', max_length=32, null=True)
    is_pre_run = models.BooleanField(default=True)
    exit_code = models.SmallIntegerField('ExitCode', null=True)
    status = models.CharField(choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value)
    command = models.TextField()
    operator = BkUserField()

    class Meta(object):
        get_latest_by = 'created'
        ordering = ['-created']
