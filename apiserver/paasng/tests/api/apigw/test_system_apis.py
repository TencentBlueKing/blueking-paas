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

from operator import attrgetter
from unittest import mock

import arrow
import pytest
from django.conf import settings
from django.test.utils import override_settings
from django.utils.translation import override
from django_dynamic_fixture import G
from rest_framework.reverse import reverse

from paas_wl.infras.cluster.models import Cluster
from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.manager import ServiceObjNotFound
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.plat_admin.system.applications import (
    query_default_apps_by_ids,
    query_legacy_apps_by_ids,
    query_uni_apps_by_ids,
    query_uni_apps_by_keyword,
    str_username,
)
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.operators import get_contact_info
from paasng.platform.engine.constants import OperationTypes
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user
from tests.utils.basic import generate_random_string
from tests.utils.helpers import create_app, create_legacy_application

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestQueryDefaultApps:
    """Test cases for querying apps in default platform"""

    def test_normal(self, bk_app):
        results = query_default_apps_by_ids(
            ids=[bk_app.code], include_inactive_apps=False, include_developers_info=True, tenant_id=DEFAULT_TENANT_ID
        )
        item = results[bk_app.code]
        assert item.name == bk_app.name
        assert item.logo_url == settings.APPLICATION_DEFAULT_LOGO, "should use default logo by default"

    def test_include_inactive_apps(self, bk_app):
        bk_app.is_active = False
        bk_app.save()

        active_apps = query_default_apps_by_ids(
            ids=[bk_app.code], include_inactive_apps=False, include_developers_info=True, tenant_id=DEFAULT_TENANT_ID
        )
        all_apps = query_default_apps_by_ids(
            ids=[bk_app.code], include_inactive_apps=True, include_developers_info=True, tenant_id=DEFAULT_TENANT_ID
        )
        item = all_apps[bk_app.code]
        assert not active_apps
        assert item.name == bk_app.name
        assert item.logo_url == settings.APPLICATION_DEFAULT_LOGO, "should use default logo by default"


class TestQueryLegacyApps:
    """Test cases for querying apps in legacy platform"""

    def test_normal(self):
        app = create_legacy_application()
        results = query_legacy_apps_by_ids(ids=[app.code], include_inactive_apps=False, include_developers_info=True)
        item = results[app.code]
        assert item.name == app.name


class TestQueryUniApps:
    """Test cases for querying apps in both platforms"""

    def test_mixed_platforms(self, bk_app):
        legacy_app = create_legacy_application()

        results = query_uni_apps_by_ids(
            ids=[bk_app.code, legacy_app.code],
            include_inactive_apps=False,
            include_developers_info=True,
            tenant_id=DEFAULT_TENANT_ID,
        )
        assert len(results) == 2
        assert results[bk_app.code].name == bk_app.name
        assert results[bk_app.code].name_en == bk_app.name_en
        assert results[bk_app.code].type == ApplicationType.DEFAULT.value
        assert results[legacy_app.code].name == legacy_app.name
        assert results[legacy_app.code].type == ApplicationType.DEFAULT.value

    @pytest.mark.parametrize(
        ("keyword", "expected_count", "language", "name_field", "tenant_id"),
        [
            ("", 2, "", "name", "default"),
            ("bk_app", 1, "en", "name_en", "default"),
            ("legacy_app", 1, "en", "name", "default"),
        ],
    )
    def test_query_by_keyword(self, bk_app, keyword, expected_count, language, name_field, tenant_id):
        keyword_app = bk_app
        legacy_app = create_legacy_application()

        if keyword == "bk_app":
            keyword = bk_app.code
        elif keyword == "legacy_app":
            keyword_app = legacy_app
            keyword = legacy_app.name

        with override(language, True):
            uni_apps_list = query_uni_apps_by_keyword(
                keyword, offset=0, limit=10, include_inactive_apps=True, tenant_id=tenant_id
            )
            assert len(uni_apps_list) == expected_count

            uni_apps_dict = {app.code: app.name for app in uni_apps_list}
            uni_apps_dict[keyword_app.code] = attrgetter(name_field)(keyword_app)


class TestTenantSysApi:
    @pytest.fixture()
    def tenant1_bk_user_app(self, bk_user):
        app = create_app(owner_username=bk_user.username)
        app.tenant_id = "tenant1"
        app.save()
        return app

    @pytest.fixture()
    def tenant2_app(self):
        app = create_app()
        app.tenant_id = "tenant2"
        app.save()
        return app

    @pytest.mark.parametrize(
        ("enable_multi_tenant", "header_tenant_id", "status_code", "expect_tenant_id"),
        [
            # 未开启多租户，请求头中不用传租户 ID，只返回租户 ID 为 default 的应用
            (False, "", 200, DEFAULT_TENANT_ID),
            # 开启多租户，请求头中不用传租户 ID，抛出 400 异常
            (True, "", 400, ""),
            (True, "tenant1", 200, "tenant1"),
            (True, "tenant2", 200, "tenant2"),
        ],
    )
    def test_query_uni_apps(
        self,
        sys_api_client,
        bk_app,
        tenant1_bk_user_app,
        tenant2_app,
        enable_multi_tenant,
        header_tenant_id,
        status_code,
        expect_tenant_id,
    ):
        with override_settings(ENABLE_MULTI_TENANT_MODE=enable_multi_tenant):
            url = reverse("sys.api.uni_applications.list_by_ids")
            headers = {
                "HTTP_X_BK_TENANT_ID": header_tenant_id,
            }
            response = sys_api_client.get(
                url, {"id": [bk_app.code, tenant1_bk_user_app.code, tenant2_app.code]}, **headers
            )
            assert response.status_code == status_code

            if response.status_code == 200:
                data = response.json()
                for d in data:
                    if d is not None:
                        assert d["tenant_id"] == expect_tenant_id

    @pytest.mark.usefixtures("bk_app")
    @pytest.mark.usefixtures("tenant1_bk_user_app")
    @pytest.mark.usefixtures("tenant2_app")
    @pytest.mark.parametrize(
        ("enable_multi_tenant", "header_tenant_id", "status_code", "expect_count", "expect_tenant_id"),
        [
            # 未开启多租户，请求头中不用传租户 ID，只返回租户 ID 为 default 的应用
            (False, "", 200, 1, DEFAULT_TENANT_ID),
            # 开启多租户，请求头中不用传租户 ID，抛出 400 异常
            (True, "", 400, 0, ""),
            (True, "tenant1", 200, 1, "tenant1"),
            # # tenant2 的应用不属于 bk_user，所以也查不到
            (True, "tenant2", 200, 0, "tenant2"),
        ],
    )
    def test_query_by_username(
        self,
        sys_api_client,
        bk_user,
        enable_multi_tenant,
        header_tenant_id,
        status_code,
        expect_count,
        expect_tenant_id,
    ):
        with override_settings(ENABLE_MULTI_TENANT_MODE=enable_multi_tenant):
            url = reverse("sys.api.uni_applications.list_by_username")
            headers = {
                "HTTP_X_BK_TENANT_ID": header_tenant_id,
            }
            response = sys_api_client.get(url, {"username": bk_user.username}, **headers)
            assert response.status_code == status_code

            if response.status_code == 200:
                data = response.json()
                assert len(data) == expect_count
                for d in data:
                    if d is not None:
                        assert d["tenant_id"] == expect_tenant_id


class TestGetContactInfo:
    """Test cases for getting app's contact info"""

    def test_normal(self, bk_app):
        contact_info = get_contact_info(bk_app)
        assert contact_info.latest_operator == bk_app.owner
        assert contact_info.recent_deployment_operators == []

    @pytest.mark.parametrize(
        ("deployment_infos", "recent_deployment_operators"),
        [
            # username, created_days_delta
            ([("user-a1", 1), ("user-b2", 10)], ["user-a1", "user-b2"]),
            # 'b2' should ignore because it was created too early
            ([("user-a1", 1), ("user-b2", 40)], ["user-a1"]),
        ],
    )
    def test_recent_deployment_operators(
        self, bk_app, bk_module, bk_stag_env, deployment_infos, recent_deployment_operators
    ):
        for username, days_delta in deployment_infos:
            user = create_user(username=username)

            # Create faked deployment and operation object
            deployment = create_fake_deployment(bk_module)
            obj = ModuleEnvironmentOperations.objects.create(
                operator=user,
                app_environment=bk_stag_env,
                application=bk_app,
                operation_type=OperationTypes.ONLINE.value,
                object_uid=deployment.pk,
            )
            ModuleEnvironmentOperations.objects.filter(pk=obj.pk).update(
                created=arrow.get().shift(days=-days_delta).datetime
            )

        contact_info = get_contact_info(bk_app)
        assert {str_username(u) for u in contact_info.recent_deployment_operators} == set(recent_deployment_operators)


class TestLessCodeSystemAPIViewSet:
    @pytest.fixture()
    def mixed_service_mgr(self):
        with mock.patch("paasng.plat_admin.system.views.mixed_service_mgr") as mgr:
            yield mgr

    @pytest.mark.parametrize(
        ("credentials", "expected_code", "expected_content"),
        [
            (
                {},
                400,
                {"code": "CANNOT_READ_INSTANCE_INFO", "detail": "读取增强服务实例信息失败: 无法获取到有效的配置信息."},
            ),
            ({"A": "B"}, 200, {"credentials": {"A": "B"}}),
        ],
    )
    def test_query_db_credentials(
        self,
        mixed_service_mgr,
        bk_app,
        bk_module,
        bk_stag_env,
        sys_lesscode_api_client,
        credentials,
        expected_code,
        expected_content,
    ):
        mixed_service_mgr.get_env_vars.return_value = credentials

        url = (
            f"/sys/api/bkapps/applications/{bk_app.code}"
            f"/modules/{bk_module.name}/envs/stag/lesscode/query_db_credentials"
        )

        response = sys_lesscode_api_client.get(url)
        assert response.status_code == expected_code
        assert response.json() == expected_content


class TestSysAddonsAPIViewSet:
    @pytest.fixture()
    def mixed_service_mgr(self):
        with mock.patch("paasng.plat_admin.system.views.mixed_service_mgr") as mgr:
            yield mgr

    @pytest.fixture()
    def service_name(self):
        return generate_random_string()

    @pytest.fixture()
    def service(self, bk_app):
        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, name="mysql", category=category, logo_b64="dummy", config={})
        # Create default plans
        G(Plan, name="plan-1", service=svc)
        return svc

    def test_query_credentials(self, bk_app, bk_module, service_name, mixed_service_mgr, sys_api_client):
        url = f"/sys/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/envs/stag/addons/{service_name}/"
        mixed_service_mgr.get_env_vars.return_value = {"FOO": "BAR"}
        response = sys_api_client.get(url)

        assert response.status_code == 200
        assert response.json() == {"credentials": {"FOO": "BAR"}}

    def test_query_credentials_404(self, bk_app, bk_module, service_name, mixed_service_mgr, sys_api_client):
        url = f"/sys/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/envs/stag/addons/{service_name}/"
        mixed_service_mgr.find_by_name.side_effect = ServiceObjNotFound

        response = sys_api_client.get(url)
        assert response.status_code == 404


class TestClusterNamespaceInfoViewSet:
    @pytest.fixture(autouse=True)
    def _create_cluster_obj(self, bk_app, _with_wl_apps):
        wl_apps = [app.wl_app for app in bk_app.envs.all()]
        for wl_app in wl_apps:
            Cluster.objects.get_or_create(
                name=wl_app.latest_config.cluster,
                defaults={"annotations": {"bcs_cluster_id": generate_random_string()}},
            )

    def test_list_by_code(self, bk_app, sys_api_client):
        url = f"/sys/api/bkapps/applications/{bk_app.code}/cluster_namespaces/"
        response = sys_api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) == 2
        assert response.data[0]["namespace"]
        assert response.data[0]["bcs_cluster_id"] is not None
