# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import string

import pytest
from bkpaas_auth.models import User
from django.test.utils import override_settings
from rest_framework import status

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.constants import AppLanguage, ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.serializers import CreateModuleSLZ
from paasng.security.access_control.models import ApplicationAccessControlSwitch
from tests.utils.auth import create_user
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SYS_APP_SPARK_URL = "/sys/api/bkapps/app_spark/"


@pytest.fixture()
def app_spark_code() -> str:
    # AppSpark 不要求前缀，按开发者中心标准规则即可
    return generate_random_string(8, string.ascii_lowercase)


@pytest.fixture()
def app_spark_name() -> str:
    return generate_random_string(8)


@pytest.fixture()
def registered_operator() -> User:
    """已在开发者中心登录过的用户，具备 UserProfile。"""
    user = create_user()
    UserProfile.objects.create(user=user.pk, tenant_id=DEFAULT_TENANT_ID, role=SiteRole.USER.value)
    return user


class TestSysCreateAppSparkApp:
    """应用态创建 AppSpark 应用接口测试"""

    def test_create_success(
        self,
        sys_app_spark_api_client,
        mock_wl_services_in_creation,
        registered_operator,
        app_spark_code,
        app_spark_name,
    ):
        """创建标准云原生应用：不是插件也不是 AI Agent，默认模块来源为 AppSpark，管理员为 operator，只创建不部署。"""
        code = app_spark_code
        resp = sys_app_spark_api_client.post(
            SYS_APP_SPARK_URL,
            data={"code": code, "name": app_spark_name, "operator": registered_operator.username},
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        body = resp.json()
        assert "bk_app_secret" not in body
        assert "secret" not in body

        app_data = body["application"]
        assert app_data["type"] == ApplicationType.CLOUD_NATIVE
        assert app_data["is_plugin_app"] is False
        assert app_data["is_ai_agent_app"] is False
        assert app_data["modules"][0]["source_origin"] == SourceOrigin.APP_SPARK

        application = Application.objects.get(code=code)
        module = application.get_default_module()
        assert module.language == AppLanguage.PYTHON.value
        assert sorted(env.environment for env in module.envs.all()) == ["prod", "stag"]
        assert not Deployment.objects.filter(app_environment__application=application).exists()
        assert not ApplicationAccessControlSwitch.objects.is_enabled(application)

        # operator 成为创建者，由创建后的信号加入管理者用户组
        assert application.creator == registered_operator.pk
        assert application.get_administrators() == [registered_operator.username]

    def test_virtual_operator_rejected(self, sys_app_spark_api_client, app_spark_code, app_spark_name):
        """没有 UserProfile 的虚拟账号不能当管理员，否则真实用户拿不到应用管理权限。"""
        virtual_user = create_user()
        assert not UserProfile.objects.filter(user=virtual_user.pk).exists()

        resp = sys_app_spark_api_client.post(
            SYS_APP_SPARK_URL,
            data={"code": app_spark_code, "name": app_spark_name, "operator": virtual_user.username},
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "operator" in resp.json()["fields_detail"]
        assert not Application.objects.filter(code=app_spark_code).exists()

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_operator_tenant_rejected(self, sys_app_spark_api_client, app_spark_code, app_spark_name):
        """operator 所属租户与应用租户不一致时返回 400。"""
        operator = create_user()
        UserProfile.objects.create(user=operator.pk, tenant_id="foo", role=SiteRole.USER.value)

        resp = sys_app_spark_api_client.post(
            SYS_APP_SPARK_URL,
            data={
                "code": app_spark_code,
                "name": app_spark_name,
                "operator": operator.username,
                "app_tenant_mode": AppTenantMode.SINGLE.value,
                "app_tenant_id": "bar",
            },
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "operator" in resp.json()["fields_detail"]
        assert not Application.objects.filter(code=app_spark_code).exists()

    def test_aidev_denied(self, sys_aidev_api_client, registered_operator, app_spark_code, app_spark_name):
        """创建接口只给 AppSpark，AIDEV 调用返回 403。"""
        resp = sys_aidev_api_client.post(
            SYS_APP_SPARK_URL,
            data={"code": app_spark_code, "name": app_spark_name, "operator": registered_operator.username},
        )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        assert not Application.objects.filter(code=app_spark_code).exists()


class TestUserFacingCreationRejectsAppSparkOrigin:
    """AppSpark 来源只能由系统 API 建出，用户态创建模块时不能指定。"""

    def test_create_module(self, bk_app):
        slz = CreateModuleSLZ(
            data={"name": "foo", "source_init_template": "dj18_hello_world", "source_origin": SourceOrigin.APP_SPARK},
            context={"application": bk_app},
        )

        assert not slz.is_valid()
        assert "source_origin" in slz.errors
