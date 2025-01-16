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

import logging
from typing import Protocol, Type

from django.conf import settings

from paasng.infras.bkmonitorv3.client import make_bk_monitor_client
from paasng.infras.bkmonitorv3.shim import get_or_create_bk_monitor_space
from paasng.misc.monitoring.monitor.models import AppDashboard, AppDashboardTemplate
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class ManagerProtocol(Protocol):
    def __init__(self, application: Application): ...

    def init_builtin_dashboard(self):
        """初始化内置仪表盘"""
        ...


class BkDashboardManager:
    """蓝鲸监控仪表盘管理器"""

    def __init__(self, application: Application):
        self.application = application
        self.app_code = self.application.code
        tenant_id = get_tenant_id_for_app(self.app_code)
        self.client = make_bk_monitor_client(tenant_id)

    def init_builtin_dashboard(self):
        """初始化内置仪表盘"""
        # 查询应用已经导入过的仪表盘
        imported_dashboard_names = set(
            AppDashboard.objects.filter(application=self.application).values_list("name", flat=True)
        )
        # 查询应用所有模块的语言
        app_languages = set(Module.objects.filter(application=self.application).values_list("language", flat=True))

        # 按应用的类型、语言查询应用还需要导入的仪表盘
        dashboard_templates = AppDashboardTemplate.objects.filter(
            is_plugin_template=self.application.is_plugin_app, language__in=app_languages
        ).exclude(name__in=imported_dashboard_names)

        space, _ = get_or_create_bk_monitor_space(Application.objects.get(code=self.app_code))
        # 导入模板中新增的仪表盘
        for template in dashboard_templates:
            self.client.import_dashboard(int(space.iam_resource_id), template.name)
            AppDashboard.objects.create(
                application=self.application,
                name=template.name,
                display_name=template.display_name,
                template_version=template.version,
                language=template.language,
            )


class NullManager:
    def __init__(self, application: Application): ...

    def init_builtin_dashboard(self): ...


def get_bk_dashboard_manager_cls() -> Type[ManagerProtocol]:
    if not settings.ENABLE_BK_MONITOR:
        logger.warning("bkmonitor in this edition not enabled, skip the built-in dashboard")
        return NullManager
    else:
        return BkDashboardManager


bk_dashboard_manager_cls = get_bk_dashboard_manager_cls()
