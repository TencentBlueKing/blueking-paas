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

from django.db import models

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.infras.bkmonitorv3.constants import SpaceType
from paasng.platform.applications.models import Application
from paasng.utils.models import UuidAuditedModel


class BKMonitorSpace(UuidAuditedModel):
    # 同一个应用 ID ，蓝鲸监控会返回相同的 space_id
    # 为了防止因为 space_id 的 unique 约束导致重新创建应用在部署时报错
    # 必须在删除应用时级联删除所有依赖的数据
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        db_constraint=False,
        related_name="bk_monitor_space",
    )

    id = models.IntegerField(verbose_name="蓝鲸监控空间 id")
    space_type_id = models.CharField(verbose_name="空间类型id", max_length=48)
    space_id = models.CharField(verbose_name="空间id", help_text="同一空间类型下唯一", max_length=48)
    space_name = models.CharField(verbose_name="空间名称", max_length=64)
    space_uid = models.CharField(
        verbose_name="蓝鲸监控空间 uid", help_text="{space_type_id}__{space_id}", max_length=48
    )
    extra_info = models.JSONField(help_text="蓝鲸监控API-metadata_get_space_detail 的原始返回值")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("space_type_id", "space_id")

    @property
    def iam_resource_id(self) -> str:
        """蓝鲸监控空间在权限中心的 资源id

        对于非 bkcc 类型的空间, 目前在 权限中心注册的 资源id 是取 空间id 的负数
        """
        if self.space_type_id != SpaceType.BKCC:
            return f"-{self.id}"
        # TODO: 确认 bkcc 类型的空间在权限中心的 资源id 是否等于 空间id
        return f"{self.id}"
