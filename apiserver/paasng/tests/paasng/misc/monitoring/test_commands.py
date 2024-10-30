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

from unittest import mock

import pytest
from django.core.management import call_command
from django.test.utils import override_settings

from paasng.infras.bkmonitorv3.client import BkMonitorClient
from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from paasng.misc.monitoring.monitor.models import AppDashboard, AppDashboardTemplate

pytestmark = pytest.mark.django_db


@pytest.fixture
def bk_monitor_space(bk_app):
    return BKMonitorSpace.objects.create(
        application=bk_app, id=1, space_type_id="bksaas", space_id="app1", extra_info={}
    )


@pytest.fixture
def init_dashboard_templates(bk_app):
    default_template = AppDashboardTemplate.objects.create(
        language=bk_app.default_module.language,
        name="bksaas/framework-python",
        display_name="Python 开发框架内置仪表盘",
        version="v1",
        is_plugin_template=False,
    )
    other_language_template = AppDashboardTemplate.objects.create(
        language="fake_language",
        name="bksaas/framework-fake_language",
        display_name="fake_language 开发框架内置仪表盘",
        version="v1",
        is_plugin_template=False,
    )
    plugin_template = AppDashboardTemplate.objects.create(
        language=bk_app.default_module.language,
        name="bksaas/plugin-fake_language",
        display_name="Python 插件内置仪表盘",
        version="v1",
        is_plugin_template=True,
    )
    return [default_template, other_language_template, plugin_template]


@pytest.mark.usefixtures("init_dashboard_templates")
def test_init_dashboard_command(
    bk_app,
    bk_monitor_space,
):
    with override_settings(ENABLE_BK_MONITOR=True), mock.patch.object(
        BkMonitorClient, "import_dashboard", return_value=None
    ):
        # 仅初始化非插件、Python 语言的仪表盘
        call_command("init_dashboards", app_codes=[bk_app.code])

    app_dashboards = AppDashboard.objects.filter(application=bk_app)
    assert app_dashboards.count() == 1
    assert app_dashboards[0].name == "bksaas/framework-python"
