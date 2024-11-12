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

from typing import Optional

from django.db import models

from paasng.platform.applications.models import Application
from paasng.utils.models import AuditedModel


class AppAlertRuleManager(models.Manager):
    def filter_app_scoped(self, app: Application, run_env: Optional[str] = None):
        qs = self.filter(application=app, module=None)
        if run_env:
            return qs.filter(environment=run_env)
        return qs

    def filter_module_scoped(self, app: Application, run_env: Optional[str] = None, module_name: Optional[str] = None):
        if module_name:
            qs = self.filter(application=app, module__name=module_name)
        else:
            qs = self.filter(application=app).exclude(module=None)

        if run_env:
            return qs.filter(environment=run_env)
        return qs


class AppAlertRule(AuditedModel):
    """记录 app 初始的告警规则配置"""

    alert_code = models.CharField(max_length=64, help_text="alert rule code e.g. high_cpu_usage")
    display_name = models.CharField(max_length=512)
    enabled = models.BooleanField(default=True)
    threshold_expr = models.CharField(max_length=64)
    receivers = models.JSONField(default=list)
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, db_constraint=False, related_name="alert_rules"
    )
    environment = models.CharField(verbose_name="部署环境", max_length=16)
    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="alert_rules", null=True
    )
    objects = AppAlertRuleManager()

    def __str__(self):
        return f"{self.display_name}-{self.alert_code}"


class AppDashboardTemplate(AuditedModel):
    """仪表盘模板，只需要记录名称和版本号，模板的内容在蓝鲸监控侧维护"""

    name = models.CharField(
        max_length=64,
        unique=True,
        help_text="与蓝鲸监控约定的仪表盘名称，如：bksaas/framework-python，需要提前将仪表盘的 JSON 文件内置到监控的代码目录中",
    )
    display_name = models.CharField(max_length=512, help_text="仪表盘展示名称，如：Python 开发框架内置仪表盘")
    version = models.CharField(max_length=32)
    language = models.CharField(verbose_name="仪表盘所属语言", max_length=32)
    is_plugin_template = models.BooleanField("是否为插件应用的模板", default=False)


class AppDashboard(AuditedModel):
    """记录 APP 初始化的仪表盘信息"""

    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, db_constraint=False, related_name="dashboards"
    )
    name = models.CharField(max_length=64, help_text="仪表盘名称，如：bksaas/framework-python")
    display_name = models.CharField(max_length=512, help_text="仪表盘展示名称，如：Python 开发框架内置仪表盘")
    template_version = models.CharField(max_length=32, help_text="模板版本更新时，可以根据该字段作为批量刷新仪表盘")
    language = models.CharField(verbose_name="仪表盘所属语言", max_length=32)

    class Meta:
        unique_together = ("application", "name")

    def __str__(self):
        return f"{self.name}-{self.application.code}"
