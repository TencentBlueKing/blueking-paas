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

import logging
from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django_dynamic_fixture import G
from rest_framework.test import APIClient

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType, ClusterFeatureFlag
from paas_wl.infras.cluster.entities import AllocationPolicy
from paas_wl.infras.cluster.models import Cluster, ClusterAllocationPolicy
from paasng.accessories.publish.market.models import Tag
from paasng.accessories.publish.sync_market.handlers import (
    on_change_application_name,
    prepare_change_application_name,
)
from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationRole, ApplicationType, AvailabilityLevel
from paasng.platform.applications.handlers import post_create_application, turn_on_bk_log_feature_for_app
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.evaluation.constants import BatchTaskStatus
from paasng.platform.evaluation.models import AppOperationReport, AppOperationReportCollectionTask
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import BuildConfig
from paasng.platform.modules.models.module import Module
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.error_codes import error_codes
from tests.utils.auth import create_user
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING
from tests.utils.helpers import create_app, generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

logger = logging.getLogger(__name__)


@pytest.fixture
def another_user(request):
    """Generate a random user"""
    user = create_user()
    return user


@pytest.fixture(autouse=True)
def _turn_on_bk_log_feature_for_app():
    post_create_application.connect(turn_on_bk_log_feature_for_app)
    yield
    post_create_application.disconnect(turn_on_bk_log_feature_for_app)


class TestMembershipViewset:
    def test_list_succeed(self, api_client, bk_app):
        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        response = api_client.get(url)
        assert len(response.data["results"]) == 1

    @pytest.mark.parametrize(
        ("role", "status", "ok"),
        [
            (..., 403, False),
            (ApplicationRole.ADMINISTRATOR, 200, True),
            (ApplicationRole.DEVELOPER, 200, True),
            (ApplicationRole.OPERATOR, 200, True),
        ],
    )
    def test_list_with_another_user(self, api_client, bk_app, bk_user, another_user, role, status, ok):
        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        if role is not ...:
            from paasng.infras.iam.helpers import add_role_members

            add_role_members(bk_app.code, role, get_username_by_bkpaas_user_id(another_user.pk))

        api_client.force_authenticate(user=another_user)
        response = api_client.get(url)
        assert response.status_code == status
        if ok:
            assert len(response.data["results"]) == 2
            test = {
                m["user"]["username"]: dict(code=bk_app.code, role=m["roles"][0]["id"])
                for m in response.data["results"]
            }
            assert test[another_user.username]["code"] == bk_app.code
            assert test[another_user.username]["role"] == role.value

    @pytest.mark.parametrize(
        ("role", "request_user_idx", "to_create_user_idx", "status"),
        [
            # success case
            (ApplicationRole.ADMINISTRATOR, 0, 1, 201),
            (ApplicationRole.DEVELOPER, 0, 1, 201),
            # invalid args
            (None, 0, 0, 400),
            (None, 0, 1, 400),
            # forbidden
            (ApplicationRole.ADMINISTRATOR, 1, 0, 403),
            (ApplicationRole.DEVELOPER, 1, 1, 403),
        ],
    )
    def test_create(
        self, api_client, bk_app, bk_user, another_user, role, request_user_idx, to_create_user_idx, status
    ):
        user_choices = [bk_user, another_user]
        cur_user = user_choices[request_user_idx]
        new_user = user_choices[to_create_user_idx]

        url = reverse("api.applications.members", kwargs=dict(code=bk_app.code))
        role_value = role.value if isinstance(role, ApplicationRole) else "invalid_role"
        data = [{"user": {"username": new_user.username, "id": new_user.pk}, "roles": [{"id": role_value}]}]

        api_client.force_authenticate(cur_user)
        response = api_client.post(url, data=data)
        assert response.status_code == status

    @pytest.mark.parametrize(
        ("another_user_role", "request_user_idx", "be_deleted_idx", "status"),
        [
            (ApplicationRole.ADMINISTRATOR, 0, 0, 204),
            (ApplicationRole.DEVELOPER, 0, 0, 400),
            (ApplicationRole.ADMINISTRATOR, 0, 1, 204),
            (ApplicationRole.DEVELOPER, 0, 1, 204),
            (ApplicationRole.ADMINISTRATOR, 1, 0, 204),
            (ApplicationRole.DEVELOPER, 1, 0, 403),
            (ApplicationRole.ADMINISTRATOR, 1, 1, 204),
            (ApplicationRole.DEVELOPER, 1, 1, 403),
        ],
    )
    def test_delete(
        self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, be_deleted_idx, status
    ):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members

        add_role_members(bk_app.code, another_user_role, get_username_by_bkpaas_user_id(another_user.pk))
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]
        user_to_delete = user_choices[be_deleted_idx]

        url = reverse("api.applications.members.detail", kwargs=dict(code=bk_app.code, user_id=user_to_delete.pk))

        api_client.force_authenticate(cur_user)
        response = api_client.delete(url)
        assert response.status_code == status

        if status == 204:
            assert len(fetch_application_members(bk_app.code)) == 1
        else:
            assert len(fetch_application_members(bk_app.code)) == 2

    @pytest.mark.parametrize(
        ("another_user_role", "request_user_idx", "status", "code"),
        [
            # 创建者也可以离开应用
            (ApplicationRole.ADMINISTRATOR, 0, 204, ...),
            (ApplicationRole.ADMINISTRATOR, 1, 204, ...),
            (ApplicationRole.DEVELOPER, 1, 204, ...),
            (ApplicationRole.ADMINISTRATOR, 2, 403, "ERROR"),
        ],
    )
    def test_level(self, api_client, bk_app, bk_user, another_user, another_user_role, request_user_idx, status, code):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members

        add_role_members(bk_app.code, another_user_role, get_username_by_bkpaas_user_id(another_user.pk))
        user_choices = [bk_user, another_user, create_user("dummy")]
        cur_user = user_choices[request_user_idx]

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == status

        user_count = 1 if status == 204 else 2
        assert len(fetch_application_members(bk_app.code)) == user_count

        if code is not ...:
            assert response.json()["code"] == code

    def test_level_last_admin(self, api_client, bk_app, bk_user, another_user):
        from paasng.infras.iam.helpers import add_role_members, fetch_application_members, remove_user_all_roles

        add_role_members(bk_app.code, ApplicationRole.ADMINISTRATOR, get_username_by_bkpaas_user_id(another_user.pk))
        remove_user_all_roles(bk_app.code, get_username_by_bkpaas_user_id(bk_user.pk))
        add_role_members(bk_app.code, ApplicationRole.DEVELOPER, get_username_by_bkpaas_user_id(bk_user.pk))
        cur_user = another_user

        url = reverse("api.applications.members.leave", kwargs=dict(code=bk_app.code))
        api_client.force_authenticate(cur_user)
        response = api_client.post(url)
        assert response.status_code == 400
        assert len(fetch_application_members(bk_app.code)) == 2
        assert response.json()["code"] == "MEMBERSHIP_DELETE_FAILED"


class TestApplicationCreateWithEngine:
    """Test application creation APIs with engine enabled"""

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.parametrize(
        ("type", "desired_type", "creation_succeeded"),
        [
            ("default", "default", True),
            ("cloud_native", "cloud_native", True),
            ("engineless_app", "engineless_app", False),
        ],
    )
    def test_create_different_types(
        self,
        type,
        desired_type,
        creation_succeeded,
        api_client,
        mock_wl_services_in_creation,
        mock_initialize_vcs_with_template,
        settings,
    ):
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/applications/v2/",
            data={
                "type": type,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_params": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS.value,
                    "source_control_type": "dft_bk_svn",
                    "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                },
            },
        )
        if creation_succeeded:
            assert response.status_code == 201
            assert response.json()["application"]["type"] == desired_type
        else:
            assert response.status_code == 400
            assert response.json()["detail"] == '已开启引擎，类型不能为 "engineless_app"'


class TestApplicationCreateWithoutEngine:
    """Test application creation APIs with engine disabled"""

    @pytest.mark.parametrize("url", ["/api/bkapps/applications/v2/", "/api/bkapps/third-party/"])
    def test_create_non_engine(self, api_client, url):
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            url,
            data={
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "engine_enabled": False,
                "market_params": {},
            },
        )
        assert response.status_code == 201
        assert response.json()["application"]["type"] == "engineless_app"


class TestApplicationUpdate:
    """Test update application API"""

    @pytest.fixture
    def _mock_change_app_name_action(self):
        # skip change app name to console
        prepare_change_application_name.disconnect(on_change_application_name)
        yield
        prepare_change_application_name.connect(on_change_application_name)

    @pytest.fixture
    def random_tenant_id(self) -> str:
        return generate_random_string(12)

    @pytest.fixture
    def _setup_random_tenant_cluster_allocation_policy(self, random_tenant_id):
        G(
            ClusterAllocationPolicy,
            type=ClusterAllocationPolicyType.UNIFORM,
            allocation_policy=AllocationPolicy(env_specific=False, clusters=[CLUSTER_NAME_FOR_TESTING]),
            tenant_id=random_tenant_id,
        )

    @pytest.fixture
    def tag(self):
        return G(Tag, name="test")

    @pytest.mark.usefixtures("_register_app_core_data")
    def test_normal(self, api_client, bk_app_full, bk_user, random_name, tag):
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app_full.code),
            data={"name": random_name, "availability_level": AvailabilityLevel.STANDARD.value, "tag_id": tag.id},
        )
        app = Application.objects.get(pk=bk_app_full.pk)
        assert response.status_code == 200
        assert app.name == random_name
        assert app.extra_info.availability_level == AvailabilityLevel.STANDARD.value
        assert app.extra_info.tag == tag

    def test_duplicated(self, api_client, bk_app, bk_user, random_name, tag):
        G(Application, name=random_name)
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app.code),
            data={"name": random_name, "availability_level": AvailabilityLevel.STANDARD.value, "tag_id": tag.id},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert f"应用名称 为 {random_name} 的应用已存在" in response.json()["detail"]

    @pytest.mark.usefixtures("_mock_change_app_name_action")
    @pytest.mark.usefixtures("_setup_random_tenant_cluster_allocation_policy")
    def test_desc_app(self, api_client, bk_user, random_name, random_tenant_id, tag):
        get_desc_handler(
            dict(
                spec_version=2,
                app={"bk_app_code": random_name, "bk_app_name": random_name},
                modules={random_name: {"is_default": True, "language": "python"}},
                tenant={"app_tenant_mode": AppTenantMode.GLOBAL, "app_tenant_id": "", "tenant_id": random_tenant_id},
            )
        ).handle_app(bk_user)
        app = Application.objects.get(code=random_name)
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(app.code),
            data={"name": random_name, "availability_level": AvailabilityLevel.STANDARD.value, "tag_id": tag.id},
        )
        assert response.status_code == 200
        # 描述文件定义的应用可以更新名称
        assert Application.objects.get(pk=app.pk).name == random_name

    @pytest.mark.usefixtures("_register_app_core_data")
    def test_invalid_availability_level(self, api_client, bk_app, bk_user, random_name):
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app.code),
            data={"name": random_name, "availability_level": "invalid_level"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert "availability_level: “invalid_level” 不是合法选项。" in response.json()["detail"]

    def test_no_tag(self, api_client, bk_app, bk_user, random_name):
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app.code),
            data={"name": random_name, "availability_level": AvailabilityLevel.STANDARD.value},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert "tag_id: 该字段是必填项" in response.json()["detail"]

    @pytest.mark.usefixtures("_register_app_core_data")
    def test_no_availability_level(self, api_client, bk_app_full, bk_user, random_name, tag):
        response = api_client.put(
            "/api/bkapps/applications/{}/".format(bk_app_full.code),
            data={"name": random_name, "tag_id": tag.id},
        )
        app = Application.objects.get(pk=bk_app_full.pk)
        assert response.status_code == 200
        assert app.name == random_name
        assert app.extra_info.availability_level is None
        assert app.extra_info.tag == tag


class TestApplicationDeletion:
    """Test delete application API"""

    @pytest.mark.usefixtures("_with_empty_live_addrs")
    def test_normal(
        self,
        api_client,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
    ):
        assert not AppOperationRecord.objects.filter(
            app_code=bk_app.code, target=OperationTarget.APP, operation=OperationEnum.DELETE
        ).exists()
        with mock.patch("paasng.platform.modules.manager.delete_module_related_res"):
            response = api_client.delete("/api/bkapps/applications/{}/".format(bk_app.code))
        assert response.status_code == 204
        assert AppOperationRecord.objects.filter(
            app_code=bk_app.code, target=OperationTarget.APP, operation=OperationEnum.DELETE
        ).exists()

    @pytest.mark.usefixtures("_with_empty_live_addrs")
    def test_rollback(
        self,
        api_client,
        bk_app,
        bk_user,
        mock_wl_services_in_creation,
    ):
        assert not AppOperationRecord.objects.filter(
            app_code=bk_app.code, target=OperationTarget.APP, operation=OperationEnum.DELETE
        ).exists()
        with mock.patch(
            "paasng.platform.applications.views.ApplicationViewSet._delete_all_module",
            side_effect=error_codes.CANNOT_DELETE_APP,
        ):
            response = api_client.delete("/api/bkapps/applications/{}/".format(bk_app.code))
        assert response.status_code == 400
        assert AppOperationRecord.objects.filter(
            app_code=bk_app.code,
            target=OperationTarget.APP,
            operation=OperationEnum.DELETE,
            result_code=ResultCode.FAILURE,
        ).exists()


class TestCreateBkPlugin:
    """Test 'bk_plugin' type application's creation"""

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.parametrize(
        ("source_init_template", "language"),
        [
            ("bk-saas-plugin-python", "Python"),
            ("bk-saas-plugin-go", "Go"),
        ],
    )
    def test_normal(self, api_client, mock_wl_services_in_creation, settings, bk_user, source_init_template, language):
        settings.IS_ALLOW_CREATE_BK_PLUGIN_APP = True
        response = self._send_creation_request(api_client, source_init_template)

        assert response.status_code == 201, f"error: {response.json()['detail']}"
        assert response.json()["application"]["is_plugin_app"] is True
        # TODO: Update tests when bk_plugin supports multiple languages
        assert response.json()["application"]["modules"][0]["language"] == language
        assert response.json()["application"]["modules"][0]["repo"] is not None

    def test_forbidden_via_config(self, api_client, settings):
        settings.IS_ALLOW_CREATE_BK_PLUGIN_APP = False
        response = self._send_creation_request(api_client)

        assert response.status_code == 400, "the creation of bk_plugin must fail"

    def _send_creation_request(self, api_client, source_init_template=""):
        random_suffix = generate_random_string(length=6)
        return api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "type": ApplicationType.CLOUD_NATIVE,
                "is_plugin_app": True,
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                "source_config": {
                    "source_control_type": "dft_gitlab",
                    "source_repo_url": "http://example.com/default/git.gi",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS.value,
                    "source_dir": "",
                    "source_init_template": source_init_template,
                },
            },
        )


class TestCreateCloudNativeApp:
    """Test 'cloud_native' type application's creation"""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_wl_services_in_creation, mock_initialize_vcs_with_template, _init_tmpls, bk_user, settings):
        pass

    def test_create_with_image(self, api_client):
        """托管方式：仅镜像"""
        random_suffix = generate_random_string(length=6)
        image_credential_name = generate_random_string(length=6)
        image_repository = "strm/helloworld-http"
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {
                    "build_config": {
                        "build_method": "custom_image",
                        "image_repository": image_repository,
                        "image_credential": {"name": image_credential_name, "password": "123456", "username": "test"},
                    },
                    "processes": [
                        {
                            "name": "web",
                            "command": ["bash", "/app/start_web.sh"],
                            "env_overlay": {
                                "stag": {"environment_name": "stag", "target_replicas": 1, "plan_name": "2C1G"},
                                "prod": {"environment_name": "prod", "target_replicas": 2, "plan_name": "2C1G"},
                            },
                        }
                    ],
                },
                "source_config": {
                    "source_origin": SourceOrigin.CNATIVE_IMAGE,
                    "source_repo_url": image_repository,
                },
            },
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"
        app_data = response.json()["application"]
        assert app_data["type"] == "cloud_native"
        assert app_data["modules"][0]["web_config"]["build_method"] == "custom_image"
        assert app_data["modules"][0]["web_config"]["artifact_type"] == "none"

        module = Module.objects.get(id=app_data["modules"][0]["id"])
        cfg = BuildConfig.objects.get_or_create_by_module(module)
        assert cfg.image_repository == image_repository
        assert cfg.image_credential_name == image_credential_name

        process_spec = ModuleProcessSpec.objects.get(module=module, name="web")
        assert process_spec.command == ["bash", "/app/start_web.sh"]
        assert process_spec.get_target_replicas("stag") == 1
        assert process_spec.get_target_replicas("prod") == 2

    @pytest.mark.usefixtures("_init_tmpls")
    @mock.patch("paasng.platform.applications.views.creation.create_new_repo")
    @mock.patch("paasng.platform.engine.configurations.building.ModuleRuntimeManager")
    @mock.patch("paasng.platform.modules.helpers.ModuleRuntimeBinder")
    @mock.patch("paasng.platform.modules.manager.delete_repo")
    @pytest.mark.parametrize(
        ("auto_create_repo", "init_error"),
        [
            # 初始化模块信息正常
            (True, False),
            (False, False),
            # 初始化异常且自动创建的仓库
            (True, True),
            # 初始化异常但未自动创建仓库
            (False, True),
        ],
    )
    def test_create_with_buildpack(
        self,
        mock_delete_repo,
        mocked_binder,
        mocked_manager,
        mock_create_new_repo,
        api_client,
        auto_create_repo,
        init_error,
    ):
        """托管方式：源码 & 镜像（使用 buildpack 进行构建）"""
        mocked_binder().bind_bp_stack.return_value = None
        mocked_manager().get_slug_builder.return_value = mock.MagicMock(is_cnb_runtime=True, environments={})

        random_suffix = generate_random_string(length=6)

        source_repo_url = "" if auto_create_repo else "https://git.example.com/helloWorld.git"
        if init_error:
            with (
                pytest.raises(RuntimeError, match="forced error"),
                mock.patch(
                    "paasng.platform.applications.views.creation.init_module_in_view",
                    side_effect=RuntimeError("forced error"),
                ),
            ):
                api_client.post(
                    "/api/bkapps/cloud-native/",
                    data={
                        "code": f"uta-{random_suffix}",
                        "name": f"uta-{random_suffix}",
                        "": True,
                        "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                        "source_config": {
                            "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                            "source_control_type": "github",
                            "auto_create_repo": auto_create_repo,
                            "source_origin": SourceOrigin.AUTHORIZED_VCS,
                            "source_repo_url": source_repo_url,
                            "source_repo_auth_info": {},
                        },
                    },
                )
        else:
            response = api_client.post(
                "/api/bkapps/cloud-native/",
                data={
                    "code": f"uta-{random_suffix}",
                    "name": f"uta-{random_suffix}",
                    "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                    "source_config": {
                        "source_init_template": settings.DUMMY_TEMPLATE_NAME,
                        "source_control_type": "github",
                        "auto_create_repo": auto_create_repo,
                        "source_origin": SourceOrigin.AUTHORIZED_VCS,
                        "source_repo_url": source_repo_url,
                        "source_repo_auth_info": {},
                    },
                },
            )
            assert response.status_code == 201, f"error: {response.json()['detail']}"
            app_data = response.json()["application"]
            assert app_data["type"] == "cloud_native"
            assert app_data["modules"][0]["web_config"]["build_method"] == "buildpack"
            assert app_data["modules"][0]["web_config"]["artifact_type"] == "image"

        if auto_create_repo:
            mock_create_new_repo.assert_called_once()
        else:
            mock_create_new_repo.assert_not_called()

        # 验证异常时的仓库清理
        if init_error and auto_create_repo:
            mock_delete_repo.assert_called_once_with("github", mock.ANY)
        else:
            mock_delete_repo.assert_not_called()

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_with_dockerfile(self, api_client):
        """托管方式：源码 & 镜像（使用 dockerfile 进行构建）"""
        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "dockerfile", "dockerfile_path": "Dockerfile"}},
                "source_config": {
                    "source_init_template": "docker",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"
        app_data = response.json()["application"]
        assert app_data["type"] == "cloud_native"
        assert app_data["modules"][0]["web_config"]["build_method"] == "dockerfile"
        assert app_data["modules"][0]["web_config"]["artifact_type"] == "image"

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_with_bk_log_feature(self, api_client, settings):
        """测试创建应用时开启日志平台功能特性"""
        cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
        cluster.feature_flags[ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR] = True
        cluster.save()

        random_suffix = generate_random_string(length=6)
        response = api_client.post(
            "/api/bkapps/cloud-native/",
            data={
                "code": f"uta-{random_suffix}",
                "name": f"uta-{random_suffix}",
                "bkapp_spec": {"build_config": {"build_method": "dockerfile", "dockerfile_path": "Dockerfile"}},
                "source_config": {
                    "source_init_template": "docker",
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert response.status_code == 201, f"error: {response.json()['detail']}"
        application = Application.objects.get(code=f"uta-{random_suffix}")
        assert application.feature_flag.has_feature(AppFeatureFlag.ENABLE_BK_LOG_COLLECTOR)


@pytest.mark.usefixtures("_init_tmpls")
@pytest.mark.usefixtures("mock_initialize_vcs_with_template")
class TestCreateApplicationWithTenantParams:
    """Test application creation with different tenant parameters and settings."""

    @pytest.fixture(autouse=True)
    def _setup_tenant_cluster_allocation_policy(self):
        for tenant_id in ["foo_tenant", DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID]:
            ClusterAllocationPolicy.objects.get_or_create(
                tenant_id=tenant_id,
                defaults={
                    "type": ClusterAllocationPolicyType.UNIFORM,
                    "allocation_policy": AllocationPolicy(env_specific=False, clusters=[CLUSTER_NAME_FOR_TESTING]),
                },
            )

    # cases start: when multi-tenant mode is disabled

    @pytest.mark.parametrize(
        ("user_tenant", "request_tenant_mode"),
        [
            (DEFAULT_TENANT_ID, AppTenantMode.GLOBAL),
            (DEFAULT_TENANT_ID, AppTenantMode.SINGLE),
            (DEFAULT_TENANT_ID, None),
            ("foo_tenant", AppTenantMode.GLOBAL),
            ("foo_tenant", AppTenantMode.SINGLE),
            ("foo_tenant", None),
        ],
    )
    def test_any_tenant_or_model_should_produce_the_same_result(
        self, user_tenant, request_tenant_mode, api_client, settings
    ):
        settings.ENABLE_MULTI_TENANT_MODE = False

        user = create_user(tenant_id=user_tenant)
        api_client.force_authenticate(user=user)
        if request_tenant_mode is None:
            data = self._build_create_params()
        else:
            data = self._build_create_params(app_tenant_mode=request_tenant_mode.value)
        response = api_client.post("/api/bkapps/cloud-native/", data=data)

        assert response.status_code == 201, f"error: {response.json()['detail']}"
        app_data = response.json()["application"]
        assert app_data["app_tenant_mode"] == AppTenantMode.SINGLE
        assert app_data["app_tenant_id"] == DEFAULT_TENANT_ID

        # Check the tenant_id of the created application object
        # TODO: Find a better way to do this assertion check.
        assert Application.objects.get(code=app_data["code"]).tenant_id == DEFAULT_TENANT_ID

    # cases start: when multi-tenant mode is enabled

    @pytest.mark.parametrize(
        ("user_tenant", "request_tenant_mode", "expected"),
        [
            # None value for 'expected' means the creation should fail
            ("foo_tenant", AppTenantMode.GLOBAL, None),
            ("foo_tenant", AppTenantMode.SINGLE, (AppTenantMode.SINGLE, "foo_tenant")),
            ("foo_tenant", None, (AppTenantMode.SINGLE, "foo_tenant")),
            (OP_TYPE_TENANT_ID, AppTenantMode.GLOBAL, (AppTenantMode.GLOBAL, "")),
            (OP_TYPE_TENANT_ID, AppTenantMode.SINGLE, (AppTenantMode.SINGLE, OP_TYPE_TENANT_ID)),
            (OP_TYPE_TENANT_ID, None, (AppTenantMode.SINGLE, OP_TYPE_TENANT_ID)),
        ],
    )
    def test_any_tenant_or_model_should_create_the_same_result(
        self, user_tenant, request_tenant_mode, expected, api_client, settings
    ):
        settings.ENABLE_MULTI_TENANT_MODE = True

        user = create_user(tenant_id=user_tenant)
        api_client.force_authenticate(user=user)
        if request_tenant_mode is None:
            data = self._build_create_params()
        else:
            data = self._build_create_params(app_tenant_mode=request_tenant_mode.value)
        response = api_client.post("/api/bkapps/cloud-native/", data=data)

        if expected is None:
            assert response.status_code == 400
            return

        assert response.status_code == 201, f"error: {response.json()['detail']}"
        app_data = response.json()["application"]
        assert app_data["app_tenant_mode"] == expected[0]
        assert app_data["app_tenant_id"] == expected[1]

        assert Application.objects.get(code=app_data["code"]).tenant_id == user_tenant

    def _build_create_params(self, **kwargs):
        """The default parameters for creating an application."""
        random_suffix = generate_random_string(length=6)
        return {
            "code": f"uta-{random_suffix}",
            "name": f"uta-{random_suffix}",
            "bkapp_spec": {"build_config": {"build_method": "dockerfile", "dockerfile_path": "Dockerfile"}},
            "source_config": {
                "source_init_template": "docker",
                "source_origin": SourceOrigin.AUTHORIZED_VCS,
                "source_repo_url": "https://github.com/octocat/helloWorld.git",
                "source_repo_auth_info": {},
            },
        } | kwargs


class TestListEvaluation:
    @pytest.fixture()
    def latest_collection_task(self) -> AppOperationReportCollectionTask:
        """
        创建采集任务测试数据
        """
        return AppOperationReportCollectionTask.objects.create(
            total_count=10,
            succeed_count=8,
            failed_count=2,
            failed_app_codes=["app1", "app2"],
            status=BatchTaskStatus.RUNNING,
        )

    @pytest.fixture()
    def app_operation_report1(self, bk_user) -> AppOperationReport:
        """
        创建应用评估详情测试数据
        """
        app = create_app(owner_username=bk_user.username)
        report = AppOperationReport.objects.create(
            cpu_requests=4000,
            mem_requests=8192,
            cpu_limits=8000,
            mem_limits=16384,
            cpu_usage_avg=0.003,
            mem_usage_avg=0.8,
            res_summary={"cpu": "1000", "mem": "2048"},
            pv=300,
            uv=150,
            latest_deployed_at=timezone.now() - timedelta(days=1),
            latest_deployer="deployer",
            latest_operated_at=timezone.now() - timedelta(days=2),
            latest_operator="operator",
            latest_operation="Deployment",
            issue_type="misconfigured",
            collected_at=timezone.now(),
            app_id=app.id,
            administrators=[],
            deploy_summary={},
            developers=["dev1", "dev2"],
            evaluate_result={"issue_type": "none"},
            visit_summary={"visits": 1000},
        )
        return report

    @pytest.fixture()
    def app_operation_report2(self, bk_user) -> AppOperationReport:
        app = create_app(owner_username=bk_user.username)
        report = AppOperationReport.objects.create(
            cpu_requests=6000,
            mem_requests=12288,
            cpu_limits=12000,
            mem_limits=24576,
            cpu_usage_avg=0.004,
            mem_usage_avg=0.1,
            res_summary={"cpu": "3000", "mem": "4096"},
            pv=500,
            uv=200,
            latest_deployed_at=timezone.now() - timedelta(days=3),
            latest_deployer="deployer",
            latest_operated_at=timezone.now() - timedelta(days=4),
            latest_operator="operator",
            latest_operation="Scaling",
            issue_type="idle",
            collected_at=timezone.now(),
            app_id=app.id,
            administrators=[],
            deploy_summary={},
            developers=["dev3", "dev4"],
            evaluate_result={"issue_type": "idle"},
            visit_summary={"visits": 1500},
        )
        return report

    @pytest.fixture()
    def inactive_app(self, bk_user) -> Application:
        app = create_app(owner_username=bk_user.username)
        app.is_active = False
        app.save()
        return app

    def test_list_evaluation(self, api_client, latest_collection_task, app_operation_report1, app_operation_report2):
        """
        测试应用评估详情列表
        """
        params = {"limit": 2, "offset": 0, "order": "pv", "issue_type": "idle"}
        response = api_client.get(reverse("api.applications.lists.evaluation"), params)

        response_data = response.json()

        assert response_data["count"] == 1

        results = response_data["results"]
        assert len(results["applications"]) == 1

        collected_at = datetime.fromisoformat(results["collected_at"].replace("Z", "+00:00"))
        assert collected_at == latest_collection_task.start_at

        app_data = results["applications"][0]
        report = app_operation_report2
        expected_app_data = {
            "code": report.app.code,
            "name": report.app.name,
            "type": report.app.type,
            "is_plugin_app": report.app.is_plugin_app,
            "logo_url": report.app.get_logo_url(),
            "cpu_limits": report.cpu_limits,
            "mem_limits": report.mem_limits,
            "cpu_usage_avg": report.cpu_usage_avg,
            "mem_usage_avg": report.mem_usage_avg,
            "pv": report.pv,
            "uv": report.uv,
            "issue_type": report.issue_type,
            "latest_operated_at": report.latest_operated_at.astimezone(timezone.get_current_timezone()).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        assert app_data == expected_app_data

    def test_issue_count(
        self, api_client, latest_collection_task, app_operation_report1, app_operation_report2, inactive_app
    ):
        """
        测试获取应用评估结果数量
        """
        response = api_client.get(reverse("api.applications.lists.evaluation.issue_count"))

        assert response.data["total"] == 3
        assert len(response.data["issue_type_counts"]) == 2

        for issue in response.data["issue_type_counts"]:
            assert issue["issue_type"] in ["none", "idle", "misconfigured"]
            assert issue["count"] == 1


class TestDeploymentModuleOrder:
    @pytest.fixture
    def bk_app(self, bk_app, bk_user) -> Application:
        """
        创建 bk_app 的第二个 module
        """
        Module.objects.create(
            application=bk_app, name="test", language="python", source_init_template="test", creator=bk_user
        )
        return bk_app

    @pytest.fixture
    def api_client_1(self, bk_app) -> APIClient:
        """
        创建第二个用户, 和APIClient, 并添加到应用的用户组
        """
        from paasng.infras.iam.constants import NEVER_EXPIRE_DAYS
        from paasng.infras.iam.members.models import ApplicationUserGroup
        from paasng.platform.applications.tenant import get_tenant_id_for_app
        from tests.utils.mocks.iam import StubBKIAMClient

        bk_user_1 = create_user()
        api_client_1 = APIClient()
        api_client_1.force_authenticate(user=bk_user_1)

        user_group = ApplicationUserGroup.objects.get(app_code=bk_app.code, role=ApplicationRole.DEVELOPER)
        tenant_id = get_tenant_id_for_app(bk_app.code)
        StubBKIAMClient(tenant_id).add_user_group_members(
            user_group.user_group_id, [bk_user_1.username], NEVER_EXPIRE_DAYS
        )
        return api_client_1

    def test_module_order(self, api_client, bk_app, api_client_1):
        """
        测试部署管理-进程列表模块自定义排序, 2个用户取得各自的排序
        """
        url = reverse("api.applications.deployment.module_order", kwargs={"code": bk_app.code})

        response = api_client.post(
            url,
            data={
                "module_orders": [
                    {
                        "module_name": "test",
                        "order": 1,
                    },
                    {
                        "module_name": "default",
                        "order": 3,
                    },
                ]
            },
        )
        assert response.data == [
            {
                "module_name": "test",
                "order": 1,
            },
            {
                "module_name": "default",
                "order": 3,
            },
        ]

        response = api_client_1.post(
            url,
            data={
                "module_orders": [
                    {
                        "module_name": "test",
                        "order": 4,
                    },
                    {
                        "module_name": "default",
                        "order": 2,
                    },
                ]
            },
        )
        assert response.data == [
            {
                "module_name": "default",
                "order": 2,
            },
            {
                "module_name": "test",
                "order": 4,
            },
        ]

        response = api_client.post(
            url,
            data={
                "module_orders": [
                    {
                        "module_name": "test",
                        "order": 3,
                    },
                    {
                        "module_name": "default",
                        "order": 1,
                    },
                ]
            },
        )
        assert response.data == [
            {
                "module_name": "default",
                "order": 1,
            },
            {
                "module_name": "test",
                "order": 3,
            },
        ]

        response = api_client_1.get(url)
        assert response.data == [
            {
                "module_name": "default",
                "order": 2,
            },
            {
                "module_name": "test",
                "order": 4,
            },
        ]

        response = api_client.get(url)
        assert response.data == [
            {
                "module_name": "default",
                "order": 1,
            },
            {
                "module_name": "test",
                "order": 3,
            },
        ]

    def test_module_order_missing_module(self, api_client, bk_app):
        """
        测试部署管理-进程列表模块自定义排序, 模块排序少传
        """
        url = reverse("api.applications.deployment.module_order", kwargs={"code": bk_app.code})

        response = api_client.post(
            url,
            data={
                "module_orders": [
                    {
                        "module_name": "test",
                        "order": 1,
                    }
                ]
            },
        )
        response_data = response.json()
        assert response_data["detail"] == "Modules missing an order: default."

    def test_module_order_extra_module(self, api_client, bk_app):
        """
        测试部署管理-进程列表模块自定义排序, 模块排序多传
        """

        url = reverse("api.applications.deployment.module_order", kwargs={"code": bk_app.code})

        response = api_client.post(
            url,
            data={
                "module_orders": [
                    {
                        "module_name": "test",
                        "order": 1,
                    },
                    {
                        "module_name": "test2",
                        "order": 2,
                    },
                ]
            },
        )
        response_data = response.json()
        assert response_data["detail"] == "No module named as test2."


class TestApplicationList:
    @pytest.fixture()
    def single_tenant_app(self, bk_user) -> Application:
        app = create_app(owner_username=bk_user.username)
        app.app_tenant_mode = AppTenantMode.SINGLE.value
        app.save()
        return app

    @pytest.fixture()
    def global_tenant_app(self, bk_user) -> Application:
        app = create_app(owner_username=bk_user.username)
        app.app_tenant_mode = AppTenantMode.GLOBAL.value
        app.save()
        return app

    def test_list_detailed(self, api_client, single_tenant_app, global_tenant_app):
        with mock.patch("paasng.platform.applications.views.application.get_exposed_links", return_value={}):
            response = api_client.get(reverse("api.applications.lists.detailed"))
            assert response.data["count"] == 2

            global_response = api_client.get(
                reverse("api.applications.lists.detailed"), {"app_tenant_mode": AppTenantMode.GLOBAL}
            )
            assert global_response.data["count"] == 1
            assert global_response.data["results"][0]["application"]["app_tenant_mode"] == AppTenantMode.GLOBAL

            single_response = api_client.get(
                reverse("api.applications.lists.detailed"), {"app_tenant_mode": AppTenantMode.SINGLE}
            )
            assert single_response.data["count"] == 1
            assert single_response.data["results"][0]["application"]["app_tenant_mode"] == AppTenantMode.SINGLE
