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
from django.db import models  # noqa
from paas_service.models import AuditedModel


class ApmData(AuditedModel):
    bk_app_code = models.CharField("蓝鲸应用ID", max_length=64)
    env = models.CharField("环境", max_length=64)
    app_name = models.CharField("APM应用名称", max_length=64)
    data_token = models.CharField("在监控申请的token", max_length=255)
    is_delete = models.BooleanField("是否已经被删除", default=False)

    class Meta:
        unique_together = ('bk_app_code', 'env')

    def __str__(self):
        return f"{self.bk_app_code}_{self.env}[{self.data_token}]"
