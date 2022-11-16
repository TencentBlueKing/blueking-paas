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
from django.db import models

from paasng.utils.models import AuditedModel


class AppAlertRule(AuditedModel):
    """记录 app 告警规则配置"""

    alert_code = models.CharField(max_length=64, help_text='alert rule code e.g. high_cpu_usage')
    display_name = models.CharField(max_length=512)
    enabled = models.BooleanField(default=True)
    threshold_expr = models.CharField(max_length=64)
    receivers = models.JSONField(default=list)
    application = models.ForeignKey(
        'applications.Application', on_delete=models.CASCADE, db_constraint=False, related_name='alert_rules'
    )
    environment = models.CharField(verbose_name='部署环境', max_length=16)
    module = models.ForeignKey(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name='alert_rules', null=True
    )

    def __str__(self):
        return f'{self.display_name}-{self.alert_code}'
