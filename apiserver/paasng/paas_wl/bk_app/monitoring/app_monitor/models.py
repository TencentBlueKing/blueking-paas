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

from paas_wl.bk_app.applications.models import AuditedModel, WlApp
from paasng.core.tenant.fields import tenant_id_field_factory


class AppMetricsMonitor(AuditedModel):
    app = models.OneToOneField(WlApp, on_delete=models.CASCADE, db_constraint=False)
    is_enabled = models.BooleanField(help_text="是否启动 AppMetrics", default=True)
    port = models.IntegerField(help_text="Service 端口")
    target_port = models.IntegerField(help_text="容器内的端口")

    tenant_id = tenant_id_field_factory()

    def disable(self):
        self.is_enabled = False
        self.save(update_fields=["is_enabled", "updated"])
