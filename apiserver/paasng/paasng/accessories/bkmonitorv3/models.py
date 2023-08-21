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
from django.db import models

from paasng.platform.applications.models import Application
from paasng.utils.models import UuidAuditedModel


class BKMonitorSpace(UuidAuditedModel):
    application = models.OneToOneField(
        Application,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_constraint=False,
        related_name="bk_monitor_space",
    )

    id = models.IntegerField(verbose_name="蓝鲸监控空间 id")
    space_type_id = models.CharField(verbose_name="空间类型id", max_length=48)
    space_id = models.CharField(verbose_name="空间id", help_text="同一空间类型下唯一", max_length=48)
    space_name = models.CharField(verbose_name="空间名称", max_length=64)
    space_uid = models.CharField(verbose_name="蓝鲸监控空间 uid", help_text="{space_type_id}_{space_id}", max_length=48)
    extra_info = models.JSONField(help_text="蓝鲸监控API-metadata_get_space_detail 的原始返回值")

    class Meta:
        unique_together = ("space_type_id", "space_id")

    @property
    def id_in_iam(self) -> str:
        """蓝鲸监控空间在权限中心的 id
        TODO: make a better name for this property

        目前的约定是将 蓝鲸监控空间id 取负数
        """
        return f"-{self.id}"
