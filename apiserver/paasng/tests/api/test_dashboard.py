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

import pytest
from django.urls import reverse

from paasng.infras.bkmonitorv3.models import BKMonitorSpace
from paasng.misc.monitoring.monitor.models import AppDashBoard

pytestmark = pytest.mark.django_db


class TestGetDashboardInfoViewSet:
    @pytest.fixture()
    def bk_monitor_space(self, bk_app):
        return BKMonitorSpace.objects.create(
            application=bk_app, id=1, space_type_id="bk_saas", space_id="app1", extra_info={}
        )

    @pytest.fixture()
    def app_dashboards(self, bk_app):
        # 先创建其他语言的仪表盘，仪表盘默认按创建时间排序
        other_language_dashboard = AppDashBoard.objects.create(
            application=bk_app,
            language="fake_language",
            name="bksaas/framework-fake_language",
            display_name="fake_language 开发框架内置仪表盘",
            template_version="v1",
        )

        default_dashboard = AppDashBoard.objects.create(
            application=bk_app,
            language=bk_app.default_module.language,
            name="bksaas/framework-python",
            display_name="Python 开发框架内置仪表盘",
            template_version="v1",
        )
        return [other_language_dashboard, default_dashboard]

    def test_get_builtin_dashboards(self, api_client, bk_app, bk_monitor_space, app_dashboards):
        url = reverse(
            "api.modules.monitor.builtin_dashboards",
            kwargs={
                "code": bk_app.code,
            },
        )
        response = api_client.get(url)
        assert response.status_code == 200
        assert "dashboard_url" in response.data[0]
        assert response.data[0]["name"] == "bksaas/framework-python"
        # 保证应用所属语言仪表盘排在前面
        assert response.data[0]["language"] == bk_app.default_module.language
