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

from paasng.platform.bkapp_model.models import ProcessComponent

pytestmark = pytest.mark.django_db


class TestProcessComponentViewSet:
    """测试进程组件视图集"""

    @pytest.fixture()
    def process_component(self):
        return ProcessComponent.objects.create(
            type="cl5",
            version="v1",
            properties_json_schema={"properties": {"enabled": {"type": "boolean", "default": False}}},
        )

    def test_list(self, plat_mgt_api_client, process_component):
        """测试获取进程组件列表"""
        url = reverse("plat_mgt.proc_components.bulk")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create(self, plat_mgt_api_client):
        """测试创建进程组件"""
        data = {
            "type": "cl5",
            "version": "v1",
            "description": "Test",
        }
        url = reverse("plat_mgt.proc_components.bulk")
        resp = plat_mgt_api_client.post(url, data=data)
        assert resp.status_code == 201

        component = ProcessComponent.objects.get(type=data["type"], version=data["version"])
        assert component.description == "Test"
        assert component.type == "cl5"

    def test_update(self, plat_mgt_api_client, process_component):
        """测试更新进程组件"""
        data = {
            "description": "Updated",
        }
        url = reverse("plat_mgt.proc_components.detail", kwargs={"uuid": process_component.uuid})

        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == 204

        component = ProcessComponent.objects.get(uuid=process_component.uuid)
        assert component.description == data["description"]

    def test_delete(self, plat_mgt_api_client, process_component):
        """测试删除进程组件"""
        url = reverse("plat_mgt.proc_components.detail", kwargs={"uuid": process_component.uuid})
        resp = plat_mgt_api_client.delete(url)
        assert resp.status_code == 204

        with pytest.raises(ProcessComponent.DoesNotExist):
            ProcessComponent.objects.get(uuid=process_component.uuid)
