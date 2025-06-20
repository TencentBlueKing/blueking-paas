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

from paasng.platform.sourcectl.models import SourceTypeSpecConfig

pytestmark = pytest.mark.django_db


def create_test_source_type_spec_data(**overrides):
    """创建测试代码库配置的默认数据"""
    default_data = {
        "name": "test_git",
        "label_zh_cn": "原生 Git",
        "label_en": "BareGit",
        "enabled": True,
        "spec_cls": "paasng.platform.sourcectl.type_specs.BareGitSourceTypeSpec",
        "server_config": {},
        "authorization_base_url": "",
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "",
        "token_base_url": "",
        "oauth_display_info_zh_cn": {},
        "oauth_display_info_en": {},
        "display_info_zh_cn": {},
        "display_info_en": {},
    }
    default_data.update(overrides)
    return default_data


class TestSourceTypeSpecViewSet:
    """测试代码库配置相关接口"""

    @pytest.fixture
    def create_source_type_spec(self):
        """辅助方法：创建一个代码库配置"""

        return G(SourceTypeSpecConfig, **create_test_source_type_spec_data())

    def test_list(self, plat_mgt_api_client, create_source_type_spec):
        """测试获取代码库配置列表接口"""

        url = reverse("plat_mgt.sourcectl.source_type_spec.list_create")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0

    def test_retrieve(self, plat_mgt_api_client, create_source_type_spec):
        """测试获取单个代码库配置详情接口"""

        pk = create_source_type_spec.pk
        url = reverse("plat_mgt.sourcectl.source_type_spec.retrieve_update_destroy", kwargs={"pk": pk})
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == create_source_type_spec.name

    def test_create(self, plat_mgt_api_client):
        """测试创建代码库配置接口"""

        url = reverse("plat_mgt.sourcectl.source_type_spec.list_create")
        custom_data = create_test_source_type_spec_data(name="custom_sourcectl", spec_cls="BareGitSourceTypeSpec")
        resp = plat_mgt_api_client.post(url, custom_data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

        tmpl = SourceTypeSpecConfig.objects.filter(name="custom_sourcectl").first()
        assert tmpl is not None

    def test_update(self, plat_mgt_api_client, create_source_type_spec):
        """测试更新代码库配置接口"""

        pk = create_source_type_spec.pk
        url = reverse("plat_mgt.sourcectl.source_type_spec.retrieve_update_destroy", kwargs={"pk": pk})
        update_data = create_test_source_type_spec_data(name="custom_sourcectl", spec_cls="BareGitSourceTypeSpec")
        resp = plat_mgt_api_client.put(url, update_data, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        tmpl = SourceTypeSpecConfig.objects.get(pk=pk)
        assert tmpl.name == update_data["name"]

    def test_delete(self, plat_mgt_api_client, create_source_type_spec):
        """测试删除代码库配置接口"""
        pk = create_source_type_spec.pk
        url = reverse("plat_mgt.sourcectl.source_type_spec.retrieve_update_destroy", kwargs={"pk": pk})
        resp = plat_mgt_api_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        with pytest.raises(SourceTypeSpecConfig.DoesNotExist):
            SourceTypeSpecConfig.objects.get(pk=pk)

    def test_get_default_configs_templates(self, plat_mgt_api_client):
        """测试获取默认配置模板接口"""
        url = reverse("plat_mgt.sourcectl.source_type_spec.default_configs_templates")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, dict)
        assert len(resp.data) > 0

    def test_get_spec_cls_choices(self, plat_mgt_api_client):
        """测试获取 spec_cls 接口"""
        url = reverse("plat_mgt.sourcectl.source_type_spec.spec_cls_choices")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0
