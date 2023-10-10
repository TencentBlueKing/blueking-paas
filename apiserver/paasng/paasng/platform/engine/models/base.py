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
import uuid
from typing import TYPE_CHECKING, Optional

from django.db import models
from django.utils import timezone

from paas_wl.platform.applications.models import WlApp
from paasng.platform.engine.constants import JobStatus
from paasng.utils.models import BkUserField, OwnerTimestampedModel, TimestampedModel

if TYPE_CHECKING:
    from paasng.platform.engine.utils.output import DeployStream

logger = logging.getLogger(__name__)


class OperationVersionBase(TimestampedModel):
    """带操作版本信息的BaseModel"""

    id = models.UUIDField('UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    operator = BkUserField()

    source_type = models.CharField(verbose_name=u'源码托管类型', max_length=16, null=True)
    source_location = models.CharField(u"代码地址", max_length=2048)
    source_version_type = models.CharField(u"代码版本类型", max_length=64)
    source_version_name = models.CharField(u"代码版本名称", max_length=64)
    source_revision = models.CharField(u"版本号", max_length=128, null=True)
    source_comment = models.TextField(u"版本说明")

    class Meta:
        abstract = True


class EngineApp(OwnerTimestampedModel):
    """蓝鲸应用引擎应用"""

    id = models.UUIDField('UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    name = models.CharField(max_length=64, unique=True)

    region = models.CharField(max_length=32)
    is_active = models.BooleanField(verbose_name='是否活跃', default=True)

    def __str__(self):
        return "{name}-{region}".format(name=self.name, region=self.region)

    def to_wl_obj(self) -> 'WlApp':
        """Return the corresponding WlApp object in the workloads module"""
        return WlApp.objects.get(region=self.region, name=self.name)


class MarkStatusMixin:
    @classmethod
    def get_event_type(cls) -> str:
        raise NotImplementedError

    @classmethod
    def to_dict(cls) -> dict:
        raise NotImplementedError

    def mark_procedure_status(self, status: 'JobStatus'):
        """针对拥有 complete_time 和 start_time 的应用标记其状态"""
        update_fields = ['status', 'updated']
        now = timezone.localtime(timezone.now())

        if status in JobStatus.get_finished_states():
            self.complete_time = now
            update_fields.append("complete_time")

            # 步骤完成的过于快速，PaaS 来不及判断其开始就已经收到了结束的标志
            if not self.start_time and not self.status:  # type: ignore
                self.start_time = now
                update_fields.append("start_time")
        else:
            self.start_time = now
            update_fields.append("start_time")

        self.status = status.value
        self.save(update_fields=update_fields)  # type: ignore

    def mark_and_write_to_stream(self, stream: 'DeployStream', status: 'JobStatus', extra_info: Optional[dict] = None):
        """标记状态，并写到 stream"""
        self.mark_procedure_status(status)
        detail = self.to_dict()
        detail.update(extra_info or {})

        stream.write_event(self.get_event_type(), detail)
