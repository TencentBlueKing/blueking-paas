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
from django_dynamic_fixture import G
from rest_framework import status

from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template

pytestmark = pytest.mark.django_db


def create_test_template_data(**overrides):
    """创建测试模板的默认数据"""
    default_data = {
        "name": "dj2_hello_world",
        "type": TemplateType.NORMAL.value,
        "display_name_zh_cn": "Django3.x 框架",
        "display_name_en": "Django3.x framework",
        "description_zh_cn": "Python + Django3.x",
        "description_en": "Python + Django3.x",
        "language": "Python",
        "market_ready": False,
        "preset_services_config": {},
        "repo_type": "",
        "source_dir": "./",
        "blob_url": "bkrepo://bkpaas3-apps-tmpls/open/dj_with_hello_world_dj2.tar.gz",
        "required_buildpacks": [],
        "processes": {},
        "tags": [],
        "repo_url": "http://test.com/test/test",
        "render_method": "django_template",
        "runtime_type": "buildpack",
        "is_display": False,
    }
    default_data.update(overrides)
    return default_data


class TestTemplateViewSet:
    """测试模板管理相关接口"""

    @pytest.fixture
    def sample_template(self) -> Template:
        """辅助方法：创建一个模板"""
        # 将模板中的 is_display 字段改为数据库中存储的 is_hidden 字段
        template_data = create_test_template_data()
        template_data["is_hidden"] = not template_data.pop("is_display")
        return G(Template, **template_data)

    def test_list(self, plat_mgt_api_client, sample_template):
        """测试获取模板列表接口"""

        url = reverse("plat_mgt.templates.list_create")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_retrieve(self, plat_mgt_api_client, sample_template):
        """测试获取单个模板详情接口"""

        pk = sample_template.pk
        url = reverse("plat_mgt.templates.retrieve_update_destroy", kwargs={"pk": pk})
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == sample_template.name

    def test_create(self, plat_mgt_api_client):
        """测试创建模板接口"""

        url = reverse("plat_mgt.templates.list_create")
        custom_data = create_test_template_data(name="custom_template", language="Go")
        resp = plat_mgt_api_client.post(url, custom_data, format="json")
        print(resp.data)
        assert resp.status_code == status.HTTP_201_CREATED

        template = Template.objects.filter(name="custom_template").first()
        assert template is not None

    def test_update(self, plat_mgt_api_client, sample_template):
        """测试更新模板接口"""

        pk = sample_template.pk
        url = reverse("plat_mgt.templates.retrieve_update_destroy", kwargs={"pk": pk})
        update_data = create_test_template_data(name="updated_template", language="Java")
        resp = plat_mgt_api_client.put(url, update_data, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # 使用 id 获取更新后的模板, 确保更新成功
        template = Template.objects.get(pk=pk)
        assert template.name == update_data["name"]

    def test_delete(self, plat_mgt_api_client, sample_template):
        """测试删除模板接口"""
        pk = sample_template.pk
        url = reverse("plat_mgt.templates.retrieve_update_destroy", kwargs={"pk": pk})
        resp = plat_mgt_api_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        with pytest.raises(Template.DoesNotExist):
            Template.objects.get(pk=pk)
