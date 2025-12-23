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

from paas_wl.utils.models import TimestampedModel
from paasng.core.tenant.fields import tenant_id_field_factory

DEFAULT_RES_QUOTA_PLAN_NAME = "default"


class ResQuotaPlan(TimestampedModel):
    """云原生资源配额方案配置模型"""

    plan_name = models.CharField("方案名称", max_length=64, unique=True)
    cpu_limit = models.CharField("CPU 限制 (millicores)", max_length=8)
    memory_limit = models.CharField("内存限制 (MiB)", max_length=8)
    cpu_request = models.CharField("CPU 请求 (millicores)", max_length=8)
    memory_request = models.CharField("内存请求 (MiB)", max_length=8)
    is_active = models.BooleanField("是否启用", default=True, db_index=True)
    is_builtin = models.BooleanField("是否为内置方案", default=False)

    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return self.plan_name
