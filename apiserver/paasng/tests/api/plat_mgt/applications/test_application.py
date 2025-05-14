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

import datetime

import pytest
from django.urls import reverse

from paas_wl.bk_app.applications.models.app import WlApp
from paas_wl.infras.cluster.constants import ClusterType
from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.publish.market.constant import AppType
from paasng.accessories.publish.market.models import Product
from paasng.accessories.publish.sync_market.handlers import register_app_core_data
from paasng.core.tenant.constants import AppTenantMode
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from tests.utils.helpers import override_settings

pytestmark = pytest.mark.django_db


class TestApplicationListView:
    """测试平台管理 - 应用列表 API"""

    @pytest.fixture
    def prepare_applications(self):
        """准备测试数据"""
        # 全局租户应用
        app1 = Application.objects.create(
            code="global-app1",
            name="全局应用1",
            type="default",
            app_tenant_id="global-tenant-1",
            app_tenant_mode=AppTenantMode.GLOBAL.value,
            is_active=True,
            created=datetime.datetime.now() - datetime.timedelta(days=1),
        )
        app2 = Application.objects.create(
            code="global-app2",
            name="全局应用2",
            type="default",
            app_tenant_id="global-tenant-2",
            app_tenant_mode=AppTenantMode.GLOBAL.value,
            is_active=True,
            created=datetime.datetime.now() - datetime.timedelta(days=2),
        )

        # 单租户应用
        app3 = Application.objects.create(
            code="single-app1",
            name="单租户应用1",
            type="engineless_app",
            app_tenant_id="tenant1",
            app_tenant_mode=AppTenantMode.SINGLE.value,
            is_active=True,
            created=datetime.datetime.now() - datetime.timedelta(days=3),
        )
        app4 = Application.objects.create(
            code="single-app2",
            name="单租户应用2",
            type="cloud_native",
            app_tenant_id="tenant1",
            app_tenant_mode=AppTenantMode.SINGLE.value,
            is_active=False,
            created=datetime.datetime.now() - datetime.timedelta(days=4),
        )
        app5 = Application.objects.create(
            code="single-app3",
            name="单租户应用3",
            type="cloud_native",
            app_tenant_id="tenant2",
            app_tenant_mode=AppTenantMode.SINGLE.value,
            is_active=False,
            created=datetime.datetime.now() - datetime.timedelta(days=5),
        )
        return {"app1": app1, "app2": app2, "app3": app3, "app4": app4, "app5": app5}

    @pytest.mark.parametrize(
        ("filter_key", "expected_count", "expected_codes"),
        [
            ({}, 5, {"single-app1", "global-app2", "global-app1", "single-app3", "single-app2"}),
            # 测试通过名称或 id 搜索
            ({"search": "全局"}, 2, {"global-app1", "global-app2"}),
            ({"search": "single"}, 3, {"single-app1", "single-app2", "single-app3"}),
            # 测试过滤条件
            ({"name": "全局"}, 2, ["global-app1", "global-app2"]),
            ({"app_tenant_id": "global-tenant-1"}, 1, ["global-app1"]),
            ({"type": "default"}, 2, ["global-app2", "global-app1"]),
            ({"app_tenant_mode": "global"}, 2, {"global-app1", "global-app2"}),
            ({"is_active": "true"}, 3, {"global-app1", "global-app2", "single-app1"}),
            # 测试排序功能
            (
                {"order_by": ["is_active", "-created"]},
                5,
                ["single-app1", "global-app2", "global-app1", "single-app3", "single-app2"],
            ),
            # 测试组合过滤
            ({"is_active": "true", "search": "全局"}, 2, {"global-app1", "global-app2"}),
            (
                {"app_tenant_mode": "single", "order_by": ["is_active", "-created"]},
                3,
                ["single-app1", "single-app3", "single-app2"],
            ),
        ],
    )
    def test_filter_list_applications(
        self, plat_mgt_api_client, prepare_applications, filter_key, expected_count, expected_codes
    ):
        """测试应用列表的过滤功能"""

        # 发送请求并验证基础响应
        rsp = plat_mgt_api_client.get(reverse("plat_mgt.applications.list_applications"), filter_key)
        assert rsp.status_code == 200
        assert rsp.data["count"] == expected_count

        # 提取并验证应用代码
        actual_codes = [item["code"] for item in rsp.data["results"]]
        if expected_count == 1:
            # 单个结果直接比较
            assert actual_codes[0] == expected_codes[0]
        else:
            # 多个结果比较集合
            assert set(actual_codes) == set(expected_codes)

    def test_list_app_types(self, plat_mgt_api_client):
        """测试获取应用类型列表"""

        url = reverse("plat_mgt.applications.types")
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert len(rsp.data) == len(ApplicationType.get_choices())

    def test_list_tenant_mode(self, plat_mgt_api_client):
        """测试获取租户模式列表"""

        url = reverse("plat_mgt.applications.list_tenant_modes")
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert len(rsp.data) == len(AppTenantMode.get_choices())

    def test_list_tenant_id(self, plat_mgt_api_client, prepare_applications):
        """测试获取租户 ID 列表"""

        url = reverse("plat_mgt.applications.list_tenant_app_statistics")

        # 测试不带查询参数的情况
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert len(rsp.data) == 3
        assert rsp.data == [
            {"tenant_id": AppTenantMode.GLOBAL.value, "app_count": 2},
            {"tenant_id": "tenant1", "app_count": 2},
            {"tenant_id": "tenant2", "app_count": 1},
        ]

        # 测试携带查询参数的情况
        rsp = plat_mgt_api_client.get(url, {"app_tenant_mode": AppTenantMode.SINGLE.value})
        assert rsp.status_code == 200
        assert len(rsp.data) == 3
        assert rsp.data == [
            {"tenant_id": AppTenantMode.GLOBAL.value, "app_count": 0},
            {"tenant_id": "tenant1", "app_count": 2},
            {"tenant_id": "tenant2", "app_count": 1},
        ]


@pytest.mark.django_db(databases=["default", "workloads"])
class TestApplicationDetailView:
    """测试平台管理 - 应用详情 API"""

    @pytest.fixture
    def clusters(self):
        """准备测试集群，并在测试完成后清理创建的集群"""
        cluster1 = Cluster.objects.create(
            name="cluster", type=ClusterType.NORMAL.value, description="test cluster", ingress_config={}
        )
        cluster2 = Cluster.objects.create(
            name="new-cluster", type=ClusterType.NORMAL.value, description="test cluster", ingress_config={}
        )

        yield cluster1, cluster2
        # 清理测试集群
        cluster1.delete()
        cluster2.delete()

    @pytest.fixture()
    def app_with_market_product(self, bk_app):
        Product.objects.create(
            code=bk_app.code,
            name_zh_cn=bk_app.name,
            name_en=bk_app.name_en,
            type=AppType.PAAS_APP.value,
        )
        register_app_core_data(sender=None, application=bk_app)
        return bk_app

    def test_get_app_detail(self, app_with_market_product, plat_mgt_api_client):
        """测试获取应用详情"""

        url = reverse("plat_mgt.applications.retrieve_app_name", kwargs={"app_code": app_with_market_product.code})
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert "basic_info" in rsp.data
        assert "modules_info" in rsp.data

    def test_update_app_name_and_sync_product(self, app_with_market_product, plat_mgt_api_client):
        """测试更新应用名称"""

        url = reverse("plat_mgt.applications.retrieve_app_name", kwargs={"app_code": app_with_market_product.code})

        # 测试中文环境下修改
        with override_settings(LANGUAGE_CODE="zh-hans"):
            rsp = plat_mgt_api_client.post(url, data={"name": "新中文名"})
            assert rsp.status_code == 204
            app_with_market_product.refresh_from_db()
            assert app_with_market_product.name == "新中文名"
            product = Product.objects.filter(code=app_with_market_product.code).first()
            assert product.name_zh_cn == app_with_market_product.name

        # 测试英文环境下修改
        with override_settings(LANGUAGE_CODE="en"):
            rsp = plat_mgt_api_client.post(url, data={"name": "new_name"})
            assert rsp.status_code == 204
            app_with_market_product.refresh_from_db()
            assert app_with_market_product.name_en == "new_name"
            product = Product.objects.get(code=app_with_market_product.code)
            assert product.name_en == app_with_market_product.name_en

    def test_update_cluster(self, bk_app, plat_mgt_api_client, clusters):
        """测试更新应用集群"""

        env = bk_app.get_default_module().envs.get(environment="prod")
        WlApp.objects.create(name=env.engine_app.name)

        url = reverse(
            "plat_mgt.applications.update_cluster",
            kwargs={"app_code": bk_app.code, "module_name": bk_app.get_default_module().name, "env_name": "prod"},
        )
        data = {"name": "new-cluster"}
        rsp = plat_mgt_api_client.post(url, data=data)
        assert rsp.status_code == 204

        # 验证集群是否更新成功
        env.refresh_from_db()
        assert env.wl_app.latest_config is not None, "latest_config is None"
        assert env.wl_app.latest_config.cluster == "new-cluster"

    def test_list_clusters(self, plat_mgt_api_client, clusters):
        """测试获取应用集群列表"""

        url = reverse("plat_mgt.applications.list_clusters")
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert len(rsp.data) > 0
