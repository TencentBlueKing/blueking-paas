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

from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import ApplicationFeatureFlag

pytestmark = pytest.mark.django_db


class TestApplicationFeatureView:
    """测试应用特性视图"""

    def test_list(self, plat_mgt_api_client, bk_app):
        """测试获取应用特性列表"""
        url = reverse("plat_mgt.applications.feature_flags", kwargs={"app_code": bk_app.code})
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_update(self, plat_mgt_api_client, bk_app):
        """测试更新应用特性"""
        url = reverse("plat_mgt.applications.feature_flags", kwargs={"app_code": bk_app.code})
        data = {
            "name": AppFeatureFlag.ACCESS_CONTROL_EXEMPT_MODE,
            "effect": True,
        }
        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 204

        # 验证特性是否更新成功
        app_feature = ApplicationFeatureFlag.objects.filter(
            application=bk_app, name=AppFeatureFlag.ACCESS_CONTROL_EXEMPT_MODE
        ).first()
        assert app_feature is not None
        assert app_feature.effect is True
