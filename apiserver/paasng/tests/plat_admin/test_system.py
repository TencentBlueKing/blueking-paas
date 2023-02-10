# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from unittest import mock

import arrow
import pytest
from django.conf import settings

from paasng.dev_resources.servicehub.manager import ServiceObjNotFound
from paasng.engine.constants import OperationTypes
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.plat_admin.system.applications import (
    get_contact_info,
    query_default_apps_by_ids,
    query_legacy_apps_by_ids,
    query_uni_apps_by_ids,
    str_username,
)
from tests.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user
from tests.utils.helpers import create_legacy_application, generate_random_string

pytestmark = pytest.mark.django_db


class TestQueryDefaultApps:
    """TestCases for querying apps in default platform"""

    def test_normal(self, bk_app):
        results = query_default_apps_by_ids(ids=[bk_app.code])
        item = results[bk_app.code]
        assert item.name == bk_app.name
        assert item.logo_url == settings.APPLICATION_DEFAULT_LOGO, 'should use default logo by default'


class TestQueryLegacyApps:
    """TestCases for querying apps in legacy platform"""

    def test_normal(self):
        app = create_legacy_application()

        results = query_legacy_apps_by_ids(ids=[app.code])
        item = results[app.code]
        assert item.name == app.name


class TestQueryUniApps:
    """TestCases for quering apps in both platforms"""

    def test_mixed_platforms(self, bk_app):
        legacy_app = create_legacy_application()

        results = query_uni_apps_by_ids(ids=[bk_app.code, legacy_app.code])
        assert len(results) == 2
        assert results[bk_app.code].name == bk_app.name
        assert results[legacy_app.code].name == legacy_app.name


class TestGetContactInfo:
    """TestCases for getting app's contact info"""

    def test_normal(self, bk_app):
        contact_info = get_contact_info(bk_app)
        assert contact_info.latest_operator == bk_app.owner
        assert contact_info.recent_deployment_operators == []

    @pytest.mark.parametrize(
        'deployment_infos,recent_deployment_operators',
        [
            # username, created_days_delta
            ([('user-a1', 1), ('user-b2', 10)], ['user-a1', 'user-b2']),
            # 'b2' should ignore because it was created too early
            ([('user-a1', 1), ('user-b2', 40)], ['user-a1']),
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
    @pytest.fixture
    def mixed_service_mgr(self):
        with mock.patch("paasng.plat_admin.system.views.mixed_service_mgr") as mgr:
            yield mgr

    @pytest.mark.parametrize(
        "credentials, expected_code, expected_content",
        [
            ({}, 400, {'code': 'CANNOT_READ_INSTANCE_INFO', 'detail': '读取增强服务实例信息失败: 无法获取到有效的配置信息.'}),
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
            f'/sys/api/bkapps/applications/{bk_app.code}'
            f'/modules/{bk_module.name}/envs/stag/lesscode/query_db_credentials'
        )

        response = sys_lesscode_api_client.get(url)
        assert response.status_code == expected_code
        assert response.json() == expected_content


class TestSysAddonsAPIViewSet:
    @pytest.fixture
    def mixed_service_mgr(self):
        with mock.patch("paasng.plat_admin.system.views.mixed_service_mgr") as mgr:
            yield mgr

    @pytest.fixture
    def service_name(self):
        return generate_random_string()

    @pytest.fixture
    def url(self, bk_app, bk_module, bk_stag_env, service_name):
        url = f'/sys/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/envs/stag/addons/{service_name}/'
        return url

    def test_query_credentials(self, mixed_service_mgr, url, sys_api_client):
        mixed_service_mgr.get_env_vars.return_value = {"FOO": "BAR"}
        response = sys_api_client.get(url)

        assert response.status_code == 200
        assert response.json() == {"credentials": {"FOO": "BAR"}}

    def test_404(self, mixed_service_mgr, url, sys_api_client):
        mixed_service_mgr.find_by_name.side_effect = ServiceObjNotFound

        response = sys_api_client.get(url)
        assert response.status_code == 404
